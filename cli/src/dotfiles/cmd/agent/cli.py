"""`dotfiles agent` commands: dashboard overview + skill/agent lint + setup."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from enum import StrEnum
from itertools import groupby

import typer
from rich.markup import escape
from rich.table import Table

from dotfiles.agent import VENDORS
from dotfiles.app.context import app_context
from dotfiles.cmd.agent.catechism import CATECHISM
from dotfiles.cmd.agent.health import HealthBootstrap, HealthError, HealthService, git_root
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentSurface,
    AgentVerify,
    CatechismEntry,
    FileValidation,
    HookRow,
    Hotspot,
    McpRow,
    PermissionRow,
    SubagentRow,
)
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.cmd.agent.setup import ALL_AGENTS, run_setup
from dotfiles.cmd.agent.skill_health import SkillHealthService
from dotfiles.cmd.agent.skill_stats import SkillStat, SkillUsageReport, SkillUsageService
from dotfiles.cmd.agent.skills import validate_skill_files
from dotfiles.cmd.agent.web_chat import GeminiChunksService, GeminiError
from dotfiles.console import console, render_steps
from dotfiles.result import StepResult

agent_app = typer.Typer(help="Agentic setup for this machine and web chats.")
# Two scopes, by where the agentic context lives:
#   this machine (direct commands)   web → browser chats
web_app = typer.Typer(help="Provision browser-chat agents with paste-able instructions.")


class _AgentChoice(StrEnum):
    """Supported agent names for `agent setup`."""

    claude = "claude"
    cursor = "cursor"
    codex = "codex"
    gemini = "gemini"
    pi = "pi"


# ---------------------------------------------------------------------------
# Glyph / render helpers (moved from cli/verify.py)
# ---------------------------------------------------------------------------

# Derived from the single VENDORS registry in dotfiles.agent — don't re-list here.
_VENDOR_HEADERS = {v.name: v.display_name for v in VENDORS}
_CLI_CONFIRMATION = {v.name: v.cli_confirmation for v in VENDORS}

_BOOL_GLYPH = {True: "[green]✓[/]", False: "[dim]—[/]"}


def _render_surface(surface: AgentSurface) -> None:
    status = surface.status
    if status == "present":
        glyph = "[green]✓[/]"
    elif status == "empty":
        glyph = "[yellow]○[/]"
    elif status == "missing":
        glyph = "[red]✗[/]"
    else:  # skipped
        glyph = "[dim]-[/]"
    console.print(f"  {glyph} [dim]{escape(surface.label):<25}[/] [dim]{escape(surface.detail)}[/]")


def _render_validation(v: FileValidation) -> None:
    if v.status == "ok":
        console.print(f"[green]OK  [/] {v.rel_path} [dim]({v.body_lines}-line body)[/]")
    elif v.status == "warn":
        console.print(f"[yellow]WARN[/] {v.rel_path}")
        for w in v.warnings:
            console.print(f"  [yellow]⚠[/] {w}")
    else:
        console.print(f"[red]FAIL[/] {v.rel_path}")
        for e in v.errors:
            console.print(f"  [red]✗[/] {e}")
        for w in v.warnings:
            console.print(f"  [yellow]⚠[/] {w}")


# ---------------------------------------------------------------------------
# Section renderers (extracted to keep overview() complexity ≤ 10)
# ---------------------------------------------------------------------------


def _render_mcp(rows: Iterable[McpRow]) -> None:
    console.print()
    console.print("[bold blue]MCP Servers[/]")
    rows_list = list(rows)
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("Server", style="dim", min_width=20)
    tbl.add_column("Claude", justify="center")
    tbl.add_column("Cursor", justify="center")
    tbl.add_column("Codex", justify="center")
    tbl.add_column("Gemini", justify="center")
    for row in rows_list:
        tbl.add_row(
            escape(row.server),
            _BOOL_GLYPH[row.claude],
            _BOOL_GLYPH[row.cursor],
            _BOOL_GLYPH[row.codex],
            _BOOL_GLYPH[row.gemini],
        )
    console.print(tbl)


def _render_hooks(rows: Iterable[HookRow]) -> None:
    console.print()
    console.print("[bold blue]Hooks[/]")
    rows_list = list(rows)
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("Event", style="dim", min_width=20)
    tbl.add_column("Claude", justify="center")
    tbl.add_column("Cursor", justify="center")
    tbl.add_column("Codex", justify="center")
    for row in rows_list:
        tbl.add_row(
            escape(row.event),
            _BOOL_GLYPH[row.claude],
            _BOOL_GLYPH[row.cursor],
            _BOOL_GLYPH[row.codex],
        )
    console.print(tbl)


def _render_agents(rows: Iterable[SubagentRow]) -> None:
    console.print()
    console.print("[bold blue]Subagents[/]")
    rows_list = list(rows)
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("Name", style="dim", min_width=20)
    tbl.add_column("Claude", justify="center")
    tbl.add_column("Codex", justify="center")
    tbl.add_column("Pi", justify="center")
    for row in rows_list:
        tbl.add_row(
            escape(row.name),
            _BOOL_GLYPH[row.claude],
            _BOOL_GLYPH[row.codex],
            _BOOL_GLYPH[row.pi],
        )
    console.print(tbl)


def _render_permissions(rows: Iterable[PermissionRow]) -> None:
    console.print()
    console.print("[bold blue]Permissions[/]")
    rows_list = list(rows)
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    for p in rows_list:
        if p.prefix_rules:
            console.print(f"  [dim]{escape(p.label)}[/]  prefix_rules={p.prefix_rules}")
        else:
            console.print(f"  [dim]{escape(p.label)}[/]  allow={p.allow}  deny={p.deny}")


def _render_vendor_surfaces(surfaces: Iterable[AgentSurface]) -> None:
    console.print()
    console.print("[bold blue]Agent Surfaces[/]")
    first = True
    for agent, group in groupby(surfaces, key=lambda s: s.agent):
        if not first:
            console.print()
        first = False
        header = _VENDOR_HEADERS.get(agent, agent)
        console.print(f"[blue]══ {header} ══[/]")
        vendor_list = list(group)
        for surface in vendor_list:
            _render_surface(surface)
        not_skipped = not (len(vendor_list) == 1 and vendor_list[0].status == "skipped")
        if not_skipped and agent in _CLI_CONFIRMATION:
            console.print(f"  [dim]{_CLI_CONFIRMATION[agent]}[/]")


def _render_overview(data: AgentOverview) -> None:
    """Render all overview sections."""
    _render_mcp(data.mcp)
    _render_hooks(data.hooks)

    s = data.skills
    console.print()
    console.print("[bold blue]Skills[/]")
    console.print(
        f"  Canonical: {s.canonical_skills}"
        f"  Claude deployed: {s.claude_deployed}"
        f"  Shared deployed: {s.shared_deployed}"
    )

    _render_agents(data.agents)

    r = data.rules
    console.print()
    console.print("[bold blue]Rules[/]")
    console.print(
        f"  Canonical: {r.canonical_rules}"
        f"  Claude deployed: {r.claude_deployed}"
        f"  Cursor deployed: {r.cursor_deployed}"
    )

    _render_permissions(data.permissions)
    _render_vendor_surfaces(data.vendor_surfaces)
    console.print()


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _render_setup_results(agent: str, results: list[StepResult]) -> None:
    """Print step results for one agent under its vendor header."""
    header = _VENDOR_HEADERS.get(agent, agent)
    console.print(f"\n[bold blue]── {header} ──[/]")
    render_steps(console, results)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

_VENDOR_ARG = typer.Argument(
    None,
    help="Agent to configure (claude/cursor/codex/gemini/pi). Omit to run all.",
)
_RESET_MCP_OPT = typer.Option(
    False,
    "--reset-mcp",
    help="Reset managed MCP entries to dotfiles defaults (claude + cursor + codex).",
)
_CLEAN_OPT = typer.Option(
    False,
    "--clean",
    help="Remove nonconforming plugins/MCPs/stale projects (claude only).",
)


def _render_vendor(v: AgentVerify) -> None:
    """Print one agent's verify summary (extracted to keep cmd_verify complexity ≤ 10)."""
    skills = f"{v.skills_deployed}/{v.skills_expected}" if v.skills_expected else "—"
    agents = f"{v.agents_deployed}/{v.agents_expected}" if v.agents_expected else "—"
    console.print(f"[bold]{v.agent}[/]  skills {skills}  agents {agents}")
    for d in v.drift:
        console.print(f"    [yellow]drift:[/] {d}")
    for probe in v.mcp:
        mark = "[green]✓[/]" if probe.ok else "[red]✗[/]"
        console.print(f"    {mark} mcp:{probe.server} [dim]{probe.detail}[/]")


@agent_app.command("verify")
def cmd_verify(
    ctx: typer.Context,
    offline: bool = typer.Option(False, "--offline", help="skip live MCP probes"),
) -> None:
    """Verify skills/agents are deployed and MCP servers are reachable."""
    app_ctx = app_context(ctx)
    verifies = SkillHealthService(
        runner=app_ctx.runner,
        http=app_ctx.http,
        dotfiles_dir=app_ctx.dotfiles_dir,
        home=app_ctx.home,
    ).verify(offline=offline)
    for v in verifies:
        _render_vendor(v)


@agent_app.command()
def setup(
    ctx: typer.Context,
    agent: _AgentChoice | None = _VENDOR_ARG,
    reset_mcp: bool = _RESET_MCP_OPT,
    clean: bool = _CLEAN_OPT,
) -> None:
    """Configure AI agent tooling (Claude Code, Cursor, Codex, Gemini, Pi)."""
    app_ctx = app_context(ctx)
    agents = [agent.value] if agent is not None else list(ALL_AGENTS)

    results = run_setup(app_ctx, agents=agents, clean=clean, reset_mcp=reset_mcp)
    for result in results:
        _render_setup_results(result.agent, result.steps)

    console.print()
    if any(result.failed for result in results):
        console.print("[red]Agent setup completed with errors.[/]")
        raise typer.Exit(1)
    console.print("[green]Agent setup complete.[/]")


@agent_app.command()
def overview(ctx: typer.Context) -> None:
    """Show the full agentic setup dashboard (MCP, hooks, skills, subagents, rules, permissions)."""
    app_ctx = app_context(ctx)

    svc = AgentOverviewService(
        runner=app_ctx.runner,
        dotfiles_dir=app_ctx.dotfiles_dir,
        home=app_ctx.home,
    )
    _render_overview(svc.overview())


@agent_app.command()
def lint(ctx: typer.Context) -> None:
    """Validate .ai/skills/ and .ai/agents/ markdown files (was: verify skills)."""
    app_ctx = app_context(ctx)

    results = validate_skill_files(app_ctx.dotfiles_dir)

    for v in results:
        _render_validation(v)

    n_fail = sum(1 for v in results if v.status == "fail")
    n_warn = sum(1 for v in results if v.status == "warn")
    n_ok = sum(1 for v in results if v.status == "ok")

    console.print()
    console.print("[dim]── Summary ──[/]")
    console.print(f"  [green]{n_ok} passed[/]")
    if n_warn:
        console.print(f"  [yellow]{n_warn} with warnings[/]")
    if n_fail:
        console.print(f"  [red]{n_fail} failed[/]")

    if n_fail:
        raise typer.Exit(1)


_STATS_SINCE = typer.Option(90, "--since", help="Window in days (default 90).")
_STATS_JSON = typer.Option(False, "--json", help="Emit raw JSON instead of the report.")


@agent_app.command()
def stats(
    ctx: typer.Context,
    since: int = _STATS_SINCE,
    json_out: bool = _STATS_JSON,
) -> None:
    """Skill-usage analytics from transcripts: leaderboard, dead skills, weak triggers."""
    app_ctx = app_context(ctx)
    svc = SkillUsageService(home=app_ctx.home, dotfiles_dir=app_ctx.dotfiles_dir)
    report = svc.report(since_days=since, now=datetime.now(UTC))
    if json_out:
        console.print_json(data=_stats_json(report))
    else:
        _render_stats(report)


def _render_stats(report: SkillUsageReport) -> None:
    days = (report.now - report.since).days
    console.print()
    console.print(
        f"[bold blue]Skill Usage[/]  [dim]{report.projects} projects · "
        f"{report.total_fires} fires · {report.sessions} sessions · last {days}d[/]"
    )
    _render_leaderboard(report.leaderboard)
    _render_weak_triggers(report.weak_triggers)
    _render_dead(report.dead)
    _render_sequences(report.sequences)
    _render_vendors(report.vendor_counts)
    if report.dropped_lines:
        console.print(f"\n[dim]({report.dropped_lines} unparseable transcript lines skipped)[/]")


def _render_leaderboard(rows: tuple[SkillStat, ...]) -> None:
    console.print()
    console.print("[bold blue]Leaderboard[/]")
    if not rows:
        console.print("  [dim](no skill invocations in window)[/]")
        return
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("Skill", style="dim", min_width=28)
    tbl.add_column("fires", justify="right")
    tbl.add_column("auto%", justify="right")
    tbl.add_column("trend")
    tbl.add_column("verdict")
    for s in rows[:15]:
        tbl.add_row(escape(s.skill), str(s.fires), f"{s.auto_pct}%", s.sparkline, s.verdict)
    console.print(tbl)


def _render_weak_triggers(rows: tuple[SkillStat, ...]) -> None:
    if not rows:
        return
    console.print()
    console.print(
        "[bold blue]⚠ Trigger health[/] [dim]— reached mostly by typing the slash command[/]"
    )
    for s in rows:
        console.print(
            f"  [yellow]{escape(s.skill)}[/]  {s.fires} fires / {s.explicit} explicit"
            "  → tighten its description:"
        )


def _render_dead(dead: tuple[str, ...]) -> None:
    if not dead:
        return
    console.print()
    console.print(
        f"[bold blue]🪦 Dead[/] [dim]— deployed, 0 fires in window ({len(dead)} candidates)[/]"
    )
    console.print("  [dim]" + " · ".join(escape(d) for d in dead) + "[/]")


def _render_sequences(sequences: tuple[tuple[tuple[str, str], int], ...]) -> None:
    if not sequences:
        return
    console.print()
    console.print("[bold blue]🔗 Sequences[/] [dim]— skills that chain[/]")
    for (first, second), count in sequences[:8]:
        console.print(f"  [dim]{escape(first)} → {escape(second)}[/]  ({count}x)")


def _render_vendors(counts: tuple[tuple[str, int], ...]) -> None:
    console.print()
    parts = "  ".join(f"{escape(v)} {n}" for v, n in counts) or "[dim](none)[/]"
    console.print(f"[bold blue]Vendors[/]  {parts}  [dim]· Cursor — (GUI, no logs)[/]")
    if any(v == "codex" for v, _ in counts):
        console.print(
            "  [dim]Codex fires = SKILL.md opens per session"
            " (autonomous; slash-invokes not separable)[/]"
        )


def _stats_json(r: SkillUsageReport) -> dict[str, object]:
    return {
        "since": r.since.isoformat(),
        "now": r.now.isoformat(),
        "total_fires": r.total_fires,
        "projects": r.projects,
        "sessions": r.sessions,
        "dropped_lines": r.dropped_lines,
        "leaderboard": [
            {
                "skill": s.skill,
                "fires": s.fires,
                "explicit": s.explicit,
                "auto_pct": s.auto_pct,
                "projects": s.projects,
                "canonical": s.canonical,
                "last_seen": s.last_seen.isoformat(),
                "verdict": s.verdict,
            }
            for s in r.leaderboard
        ],
        "dead": list(r.dead),
        "weak_triggers": [s.skill for s in r.weak_triggers],
        "sequences": [{"from": a, "to": b, "count": n} for (a, b), n in r.sequences],
        "vendors": dict(r.vendor_counts),
    }


_HEALTH_SCOPE = typer.Option("repo", "--scope", help="Health scope name (docs/health/<scope>/).")
_HEALTH_GLOB = typer.Option(
    "**/*", "--glob", help="files_glob the ratchet counts over (e.g. 'src/**/*.py')."
)
_HEALTH_RUN_FROM = typer.Option(
    ".", "--run-from", help="Dir the glob is relative to (e.g. 'cli/')."
)
_HEALTH_FORCE = typer.Option(
    False, "--force", help="Reseed baselines.json even if it exists (re-counts ceilings)."
)


@agent_app.command()
def health(
    ctx: typer.Context,
    scope: str = _HEALTH_SCOPE,
    glob: str = _HEALTH_GLOB,
    run_from: str = _HEALTH_RUN_FROM,
    force: bool = _HEALTH_FORCE,
) -> None:
    """Bootstrap a repo's code-health backbone: scorecard → baselines.json + findings.md."""
    app_ctx = app_context(ctx)
    svc = HealthService(
        runner=app_ctx.runner,
        scripts_dir=app_ctx.dotfiles_dir / "ai" / "skills" / "converge" / "scripts",
    )
    try:
        target = git_root(app_ctx.runner)
        result = svc.bootstrap(
            target=target,
            scope=scope,
            files_glob=glob,
            run_from=run_from,
            today=date.today(),
            force=force,
        )
    except HealthError as exc:
        console.print(f"[red]error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    _render_health(result)


def _render_health(r: HealthBootstrap) -> None:
    console.print()
    console.print(f"[bold blue]Code-health backbone[/]  [dim]scope: {escape(r.scope)}[/]")
    console.print(f"  repo  [dim]{escape(r.target)}[/]")
    console.print(f"  LOC {r.scorecard.loc}   suppressions {r.total_suppressions}")
    if r.created:
        console.print(f"  [green]✓[/] baselines  [dim]{escape(r.baselines_path)}[/]")
    else:
        console.print(
            f"  [yellow]○[/] baselines exist — kept (--force to reseed)  "
            f"[dim]{escape(r.baselines_path)}[/]"
        )
    console.print(f"  [green]✓[/] findings   [dim]{escape(r.findings_path)}[/]")
    _render_hotspots(r.scorecard.hotspots)
    console.print()
    console.print(
        "[dim]Next: run [/][bold]/converge[/][dim] to grade (report-<date>.md) "
        "and populate the findings backlog.[/]"
    )


def _render_hotspots(rows: tuple[Hotspot, ...]) -> None:
    if not rows:
        return
    console.print()
    console.print("[bold blue]Hotspots[/] [dim]— churn*LOC; spend refactor effort here first[/]")
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("score", justify="right")
    tbl.add_column("churn", justify="right")
    tbl.add_column("loc", justify="right")
    tbl.add_column("file", style="dim")
    for h in rows[:8]:
        tbl.add_row(str(h.score), str(h.churn), str(h.loc), escape(h.file))
    console.print(tbl)


@agent_app.command()
def catechism(ctx: typer.Context) -> None:
    """The code-health Catechism: symptom → the rite to reach for (the entry-point map)."""
    app_context(ctx)  # validate context; the catechism itself is static
    _render_catechism(CATECHISM)


def _render_catechism(entries: tuple[CatechismEntry, ...]) -> None:
    console.print()
    console.print(
        "[bold blue]The Catechism[/] [dim]— believe the Canon, practice this. "
        "Front door: [/][bold]code-health[/][dim].[/]"
    )
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("You want to…", style="dim", max_width=48)
    tbl.add_column("Reach for")
    tbl.add_column("Tier · kind", style="dim")
    for e in entries:
        tbl.add_row(escape(e.symptom), f"[bold]{escape(e.rite)}[/]", escape(e.tier))
    console.print(tbl)
    console.print(
        "\n[dim]The doctrine behind it: CANON.md · the theory: code-health-portfolio.md[/]"
    )


@web_app.command("copy")
def web_copy(
    ctx: typer.Context,
    list_chunks: bool = typer.Option(
        False, "--list", help="Print chunk filenames and sizes, then exit."
    ),
    step: bool = typer.Option(
        False, "--step", help="Interactive: copy each chunk and wait for enter."
    ),
) -> None:
    """Copy system-instruction chunks to the clipboard for a web chat (Gemini saved-info)."""
    app_ctx = app_context(ctx)

    svc = GeminiChunksService(
        runner=app_ctx.runner,
        chunks_dir=app_ctx.dotfiles_dir / "ai" / "prompts" / "gemini-chunks",
    )

    try:
        if list_chunks:
            _gemini_list(svc)
        elif step:
            _gemini_step(svc)
        else:
            _gemini_flycut(svc)
    except GeminiError as exc:
        console.print(f"[red]error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc


def _gemini_list(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print("[bold blue]Gemini chunks[/] (target: ~1500 chars each)\n")
    for chunk in chunks:
        console.print(f"  {chunk.char_count:>4} chars  {escape(chunk.name)}")


def _gemini_step(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print(
        "[bold blue]Interactive mode[/]: copy each chunk, paste into Gemini Saved Info,"
        " then press enter."
    )
    console.print("Open https://gemini.google.com/saved-info in another window.\n")
    for chunk in chunks:
        svc.copy(chunk.content)
        console.print(f"[green]Copying {escape(chunk.name)}[/] ({chunk.char_count} chars)")
        typer.prompt(
            "  paste it as a new Saved Info entry, then press enter for next…",
            default="",
            prompt_suffix="",
        )
    console.print(f"\n[green]done[/] — all {len(chunks)} chunks copied.")


def _gemini_flycut(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print(
        f"[bold blue]Loading {len(chunks)} chunks into clipboard history (for Flycut)…[/]"
    )
    for chunk in reversed(chunks):
        svc.copy(chunk.content)
        console.print(f"  [green]✓[/]  {escape(chunk.name)} ({chunk.char_count} chars)")
        svc.wait(0.4)
    console.print(
        "\nNext:\n"
        "  1. Open https://gemini.google.com/saved-info\n"
        "  2. Open Flycut (default shortcut: cmd+shift+V)\n"
        '  3. For each entry in Flycut history (top is chunk 01), click "Add new"\n'
        "     in Gemini, paste, and save.\n"
        "\nIf your Flycut history didn't catch all 7, re-run with --step instead."
    )


agent_app.add_typer(web_app, name="web")
