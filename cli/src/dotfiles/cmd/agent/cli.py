"""`dotfiles agent` commands: dashboard overview + skill/agent lint + setup."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

import typer
from rich.markup import escape

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.agent.capability_matrix import capability_rows, receipts
from dotfiles.cmd.agent.health import HealthError, HealthService, git_root
from dotfiles.cmd.agent.instructions import build_manifest
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.cmd.agent.render.health import (
    gemini_flycut,
    gemini_list,
    gemini_step,
    render_health,
    render_setup_results,
    render_validation,
    render_vendor,
    verify_capability_probes,
)
from dotfiles.cmd.agent.render.instructions import manifest_json, render_instructions
from dotfiles.cmd.agent.render.overview import (
    CAP_GLYPH,
    GOLD,
    render_capability_matrix,
    render_overview,
)
from dotfiles.cmd.agent.render.skills import (
    ORIGIN_STYLE,
    order_by_origin,
    render_collision_report,
    render_orphans,
    render_skills,
)
from dotfiles.cmd.agent.render.stats import render_stats, stats_json
from dotfiles.cmd.agent.setup import ALL_AGENTS, run_setup
from dotfiles.cmd.agent.skill_collision import collision_report
from dotfiles.cmd.agent.skill_health import SkillHealthService
from dotfiles.cmd.agent.skill_inventory import inventory
from dotfiles.cmd.agent.skill_prune import find_orphans, prune_orphans
from dotfiles.cmd.agent.skill_stats import SkillUsageService
from dotfiles.cmd.agent.skills import validate_skill_files
from dotfiles.cmd.agent.web_chat import GeminiChunksService, GeminiError
from dotfiles.console import console, print_section, print_status, print_title, render_steps

agent_app = typer.Typer(cls=FuzzyTyperGroup, help="Agentic setup for this machine and web chats.")
# Two scopes, by where the agentic context lives:
#   this machine (direct commands)   web → browser chats
web_app = typer.Typer(
    cls=FuzzyTyperGroup, help="Provision browser-chat agents with paste-able instructions."
)


class _AgentChoice(StrEnum):
    """Supported agent names for `agent setup`."""

    claude = "claude"
    cursor = "cursor"
    codex = "codex"
    gemini = "gemini"
    pi = "pi"
    hermes = "hermes"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

_VENDOR_ARG = typer.Argument(
    None,
    help="Agent to configure (claude/cursor/codex/gemini/pi/hermes). Omit to run all.",
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
        render_vendor(v)


@agent_app.command()
def setup(
    ctx: typer.Context,
    agent: _AgentChoice | None = _VENDOR_ARG,
    reset_mcp: bool = _RESET_MCP_OPT,
    clean: bool = _CLEAN_OPT,
    prune: bool = typer.Option(
        False, "--prune", help="After deploying, delete retired skills so dirs mirror canonical."
    ),
) -> None:
    """Configure AI agent tooling (Claude Code, Cursor, Codex, Gemini, Pi, Hermes)."""
    app_ctx = app_context(ctx)
    agents = [agent.value] if agent is not None else list(ALL_AGENTS)

    results = run_setup(app_ctx, agents=agents, clean=clean, reset_mcp=reset_mcp)
    for result in results:
        render_setup_results(result.agent, result.steps)

    if prune:
        orphans = find_orphans(app_ctx.runner, app_ctx.home, app_ctx.dotfiles_dir)
        retired = [o for o in orphans if o.origin == "retired"]
        if retired:
            print_section(
                console, "Prune", "retired skills removed so deployed dirs mirror canonical"
            )
            render_steps(console, prune_orphans(orphans, dry_run=False))

    console.print()
    if any(result.failed for result in results):
        print_status(console, "error", "Agent setup completed with errors.")
        raise typer.Exit(1)
    print_status(console, "success", "Agent setup complete.")


@agent_app.command()
def overview(ctx: typer.Context) -> None:
    """Show the full agentic setup dashboard (MCP, hooks, skills, subagents, rules, permissions)."""
    app_ctx = app_context(ctx)

    svc = AgentOverviewService(
        runner=app_ctx.runner,
        dotfiles_dir=app_ctx.dotfiles_dir,
        home=app_ctx.home,
    )
    render_overview(svc.overview(), app_ctx.home)


@agent_app.command()
def capabilities(
    ctx: typer.Context,
    verify: bool = typer.Option(
        False, "--verify", help="Run each cell's local probe and report proven/failed."
    ),
) -> None:
    """The capability matrix with its evidence — a probe and/or source URL per cell.

    The matrix is provenance-backed: `--verify` runs the on-machine probes so the
    claims stay tethered to what's actually installed.
    """
    app_ctx = app_context(ctx)
    print_title(console, "agent", "capabilities")
    render_capability_matrix(capability_rows())
    print_section(console, "Receipts", "probe (on-machine) · source (documentary) per cell")
    for cap, agent, cell in receipts():
        proof = cell.test or cell.src
        kind = "probe" if cell.test else "src"
        console.print(
            f"  [{GOLD}]{escape(cap):<18}[/] [dim]{escape(agent):<7}[/] "
            f"[{CAP_GLYPH.get(cell.status, ('?', 'dim'))[1]}]{cell.status:<10}[/] "
            f"[dim]{kind}:[/] {escape(proof)}"
        )
    if verify:
        verify_capability_probes(app_ctx.runner)


@agent_app.command()
def lint(ctx: typer.Context) -> None:
    """Validate .ai/skills/ and .ai/agents/ markdown files (was: verify skills)."""
    app_ctx = app_context(ctx)

    results = validate_skill_files(app_ctx.dotfiles_dir)

    print_title(console, "agent", "lint")
    for v in results:
        render_validation(v)

    n_fail = sum(1 for v in results if v.status == "fail")
    n_warn = sum(1 for v in results if v.status == "warn")
    n_ok = sum(1 for v in results if v.status == "ok")

    print_section(console, "Summary")
    console.print(f"  [green]{n_ok} passed[/]")
    if n_warn:
        console.print(f"  [yellow]{n_warn} with warnings[/]")
    if n_fail:
        console.print(f"  [red]{n_fail} failed[/]")

    if n_fail:
        raise typer.Exit(1)


# `agent skills` (list) + `agent skills prune` — skills is its own sub-app.
skills_app = typer.Typer(cls=FuzzyTyperGroup, help="List skills by origin, and prune retired ones.")


@skills_app.callback(invoke_without_command=True)
def skills_list(
    ctx: typer.Context,
    show_all: bool = typer.Option(
        False, "--all", "-a", help="Include vendor-shipped builtin skills (hidden by default)."
    ),
) -> None:
    """List every skill grouped by origin, then alphabetically by name.

    Vendor-shipped builtins (Cursor/Codex natives) aren't ours to manage, so
    they're hidden by default — the listing shows what we own and decide. Pass
    ``--all`` to include them.
    """
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = app_context(ctx)
    items = inventory(app_ctx.runner, app_ctx.home, app_ctx.dotfiles_dir)
    print_title(console, "agent", "skills")
    if not items:
        print_status(console, "info", "No skills found")
        return
    hidden_builtin = 0 if show_all else sum(1 for s in items if s.origin == "builtin")
    if not show_all:
        items = [s for s in items if s.origin != "builtin"]
    items = order_by_origin(items)
    counts: dict[str, int] = {}
    for s in items:
        counts[s.origin] = counts.get(s.origin, 0) + 1
    tally = "  ".join(f"[{ORIGIN_STYLE[o]}]{o} {counts[o]}[/]" for o in ORIGIN_STYLE if o in counts)
    console.print(f"  {len(items)} skills · {tally}")
    if hidden_builtin:
        console.print(f"  [dim]+ {hidden_builtin} vendor builtin hidden · --all to show[/]")
    console.print()
    render_skills(items)


@skills_app.command("audit")
def skills_audit(ctx: typer.Context) -> None:
    """Audit likely trigger collisions between owned skills and Pi package skills."""
    app_ctx = app_context(ctx)
    print_title(console, "agent", "skills", "audit")
    render_collision_report(collision_report(home=app_ctx.home, dotfiles_dir=app_ctx.dotfiles_dir))


@skills_app.command("prune")
def skills_prune(
    ctx: typer.Context,
    apply: bool = typer.Option(
        False, "--apply", help="Delete retired skills (default: dry-run preview)."
    ),
) -> None:
    """Remove deployed skills that were ours but are no longer canonical (mirror, not append)."""
    app_ctx = app_context(ctx)
    orphans = find_orphans(app_ctx.runner, app_ctx.home, app_ctx.dotfiles_dir)
    print_title(console, "agent", "skills", "prune")
    if not orphans:
        print_status(console, "success", "Deployed skills already mirror canonical — nothing to do")
        return
    render_orphans(orphans)
    retired = [o for o in orphans if o.origin == "retired"]
    if not retired:
        print_status(console, "info", "Nothing retired to prune")
        return
    if apply:
        print_section(console, "Removed")
        render_steps(console, prune_orphans(orphans, dry_run=False))
    else:
        print_status(
            console, "info", f"{len(retired)} retired skill(s) — re-run with `--apply` to delete"
        )


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
        console.print_json(data=stats_json(report))
    else:
        render_stats(report)


_HEALTH_SCOPE = typer.Option("repo", "--scope", help="Health scope name (docs/health/<scope>/).")
_HEALTH_GLOB = typer.Option(
    "", "--glob", help="files_glob override (default: detected from the language pack)."
)
_HEALTH_RUN_FROM = typer.Option(
    "", "--run-from", help="Dir the glob is relative to (default: the pack's, usually '.')."
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
            files_glob=glob or None,
            run_from=run_from or None,
            today=date.today(),
            force=force,
        )
    except HealthError as exc:
        console.print(f"[red]error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    render_health(result)


@agent_app.command()
def catechism(ctx: typer.Context) -> None:
    """Subsumed into `agent instructions` — its doctrine + routing now live in that tree."""
    app_ctx = app_context(ctx)
    print_title(console, "agent", "instructions")
    console.print("[dim](catechism is now part of [/]instructions[dim] — showing it)[/]\n")
    render_instructions(build_manifest(app_ctx.dotfiles_dir))


@agent_app.command()
def instructions(
    ctx: typer.Context,
    json_out: bool = typer.Option(False, "--json", help="Emit the raw manifest as JSON."),
) -> None:
    """The harness manifest as a tree: what an agent is fed, and what it can reach.

    The five-layer harness model, then a tree of context — *in context now* (the
    budget every session pays), *reachable on demand* (zero cost until pulled), the
    *active harness* (hooks/deny/permissions/MCP), and the *tool surface* — with the
    engineering map + symptom→rite routing folded in (subsuming `catechism`) and the
    vendors that skip a surface flagged inline.
    """
    app_ctx = app_context(ctx)
    manifest = build_manifest(app_ctx.dotfiles_dir)
    if json_out:
        console.print_json(data=manifest_json(manifest))
        return
    print_title(console, "agent", "instructions")
    render_instructions(manifest)
    console.print(
        "\n[dim]Sibling: [/]overview[dim] (per-vendor deploy state) · the map: ENGINEERING.md[/]"
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
            gemini_list(svc)
        elif step:
            gemini_step(svc)
        else:
            gemini_flycut(svc)
    except GeminiError as exc:
        console.print(f"[red]error:[/] {escape(str(exc))}")
        raise typer.Exit(1) from exc


agent_app.add_typer(skills_app, name="skills")
agent_app.add_typer(web_app, name="web")
