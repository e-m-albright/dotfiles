"""`dotfiles agent` commands: dashboard overview + skill/agent lint + setup."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from enum import StrEnum
from itertools import groupby
from pathlib import Path

import typer
from rich.markup import escape
from rich.table import Table

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.agent import OVERVIEW_AGENTS, OVERVIEW_COLS, VENDORS
from dotfiles.app.context import app_context
from dotfiles.cmd.agent.capability_matrix import (
    FLEET_STALE_DAYS as _FLEET_STALE_DAYS,
)
from dotfiles.cmd.agent.capability_matrix import (
    CapabilityRow,
    Cell,
    capability_rows,
    receipts,
)
from dotfiles.cmd.agent.catechism import (
    CATECHISM,
    DOCTRINE,
    DoctrineLayer,
    ScopeHealth,
    read_scope_health,
)
from dotfiles.cmd.agent.health import HealthBootstrap, HealthError, HealthService, git_root
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentSurface,
    AgentVerify,
    CatechismEntry,
    FileValidation,
    Hotspot,
    PermissionRow,
    PluginRow,
    UniformityRow,
    ValueRow,
)
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.cmd.agent.setup import ALL_AGENTS, run_setup
from dotfiles.cmd.agent.skill_collision import (
    SkillCollision,
    SkillCollisionReport,
    collision_report,
)
from dotfiles.cmd.agent.skill_health import SkillHealthService
from dotfiles.cmd.agent.skill_inventory import SkillInfo, inventory
from dotfiles.cmd.agent.skill_prune import SkillOrphan, find_orphans, prune_orphans
from dotfiles.cmd.agent.skill_stats import SkillStat, SkillUsageReport, SkillUsageService
from dotfiles.cmd.agent.skills import validate_skill_files
from dotfiles.cmd.agent.web_chat import GeminiChunksService, GeminiError
from dotfiles.console import console, print_section, print_status, print_title, render_steps
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

# Brand gold for soft attribute/value text (replaces the hard-to-read dim grey).
_GOLD = "#cdbf80"
# Fixed agent column order for every matrix.
_AGENT_COLS: tuple[str, ...] = OVERVIEW_AGENTS
_COL_W = 8
_LABEL_W = 24
# Which agents each surface applies to; others render "·" (n/a), never "✗".
_MCP_AGENTS = {"claude", "codex"}  # the only vendors we deploy MCP to (granola); rest n/a
_HOOK_AGENTS = {"claude", "cursor", "codex"}
# Vendors with a `.md` subagents directory we deploy to. Cursor 2.4+ reads
# ~/.cursor/agents; agy defines subagents inline (no .md dir) so it stays out.
_SUBAGENT_AGENTS = {"claude", "codex", "cursor", "pi"}
_STATUS_GLYPH = {
    "present": "[green]✓[/]",
    "empty": "[yellow]○[/]",
    "missing": "[red]✗[/]",
    "skipped": "[dim]·[/]",
}


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
# Overview rendering — uniform matrices (all agents) + per-agent surface tables
# ---------------------------------------------------------------------------


def _tilde(path: str, home: Path) -> str:
    """Home-relative display (~/…) for a path; unchanged if outside home."""
    try:
        return "~/" + str(Path(path).relative_to(home))
    except ValueError:
        return path


def _path_link(path: str, home: Path) -> str:
    """A clickable file:// link, shown home-relative and dimmed."""
    if not path:
        return ""
    return f"[link=file://{path}][dim]{escape(_tilde(path, home))}[/dim][/link]"


def _matrix_header(title: str) -> None:
    cols = "".join(OVERVIEW_COLS.get(a, a).center(_COL_W) for a in _AGENT_COLS)
    head = f"▸ {title}"
    pad = " " * max(1, 2 + _LABEL_W - len(head))
    console.print(f"\n[bold]{escape(head)}[/]{pad}[dim]{cols}[/]")


def _ov_section(title: str, hint: str | None = None) -> None:
    line = f"\n[bold]▸ {escape(title)}[/]"
    if hint:
        line += f"  [dim]{escape(hint)}[/]"
    console.print(line)


def _state_cell(present: bool, applies: bool) -> str:
    if not applies:  # surface doesn't exist for this agent — n/a, not a failure
        return f"[dim]{'·'.center(_COL_W)}[/]"
    glyph, color = ("✓", "green") if present else ("✗", "red")
    return f"[{color}]{glyph.center(_COL_W)}[/]"


def _render_state_matrix(
    title: str, rows: Iterable[object], applies: set[str], label_attr: str
) -> None:
    rows_list = list(rows)
    if not rows_list:
        _ov_section(title)
        console.print("  [dim](none)[/]")
        return
    _matrix_header(title)
    for row in rows_list:
        label = str(getattr(row, label_attr, ""))
        cells = "".join(
            _state_cell(bool(getattr(row, a, False)), a in applies) for a in _AGENT_COLS
        )
        console.print(f"  {escape(label):<{_LABEL_W}}{cells}")


_CAP_GLYPH: dict[str, tuple[str, str]] = {
    "yes": ("✓", "green"),  # supported (GA) — receipt in the cell
    "beta": ("◐", "yellow"),  # preview / partial / auto-only
    "ext": ("⊕", "cyan"),  # supported only via an extension (Pi)
    "no": ("✗", "red"),  # proven absent (with evidence)
    "unverified": ("?", "dim"),  # no first-party source AND not locally probeable
}


def _capability_cell(cell: Cell) -> str:
    glyph, color = _CAP_GLYPH.get(cell.status, ("?", "dim"))
    return f"[{color}]{glyph.center(_COL_W)}[/]"


def _render_capability_matrix(rows: Iterable[CapabilityRow]) -> None:
    """Cross-vendor capability matrix — vendor support, each cell provenance-backed."""
    rows_list = list(rows)
    if not rows_list:
        return
    _matrix_header("Capability matrix")
    for row in rows_list:
        cells = "".join(_capability_cell(row.cells[a]) for a in _AGENT_COLS)
        console.print(f"  {escape(row.capability):<{_LABEL_W}}{cells}")
    console.print(
        "  [dim][green]✓[/green] supported · [yellow]◐[/yellow] beta/partial · "
        "[cyan]⊕[/cyan] via extension · [red]✗[/red] absent (proven) · ? unverified[/]\n"
        "  [dim]evidence (probe / source per cell): dotfiles agent capabilities[/]"
    )


_COVERAGE_GLYPH: dict[str, tuple[str, str]] = {
    "active": ("✓", "green"),  # supported AND deployed (or native to the vendor)
    "gap": ("✗", "red"),  # supported, not deployed, CLOSABLE by a global deploy
    "local": ("○", "yellow"),  # supported but only workspace-local/extension/beta
    "na": ("·", "dim"),  # vendor doesn't support it
}


def _coverage_cell(state: str) -> str:
    glyph, color = _COVERAGE_GLYPH.get(state, ("·", "dim"))
    return f"[{color}]{glyph.center(_COL_W)}[/]"


def _render_uniformity_matrix(rows: Iterable[UniformityRow]) -> None:
    """Enforced-tier coverage: deployed (✓) vs closable gap (✗) vs not-globally-closable (○)."""
    rows_list = list(rows)
    if not rows_list:
        return
    _matrix_header("Uniformity (enforced)")
    for row in rows_list:
        cells = "".join(_coverage_cell(row.cells.get(a, "na")) for a in _AGENT_COLS)
        console.print(f"  {escape(row.capability):<{_LABEL_W}}{cells}")
    console.print(
        "  [dim][green]✓[/green] deployed · [red]✗[/red] closable gap · "
        "[yellow]○[/yellow] supported but workspace-local/ext/beta · · n/a[/]"
    )


def _render_value_matrix(title: str, rows: Iterable[ValueRow]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    _matrix_header(title)
    for row in rows_list:
        cells = "".join(f"[{_GOLD}]{row.cells.get(a, '—').center(_COL_W)}[/]" for a in _AGENT_COLS)
        console.print(f"  {escape(row.label):<{_LABEL_W}}{cells}")


def _render_plugins(rows: Iterable[PluginRow]) -> None:
    rows_list = list(rows)
    _ov_section("Plugins", "Claude Code marketplace · ⚠ = installed but not in plugins.yaml")
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    for p in rows_list:
        mark = "[green]✓[/]" if p.declared else "[yellow]⚠[/]"
        console.print(
            f"  {mark} [{_GOLD}]{escape(p.name):<26}[/] "
            f"{escape(p.version or '—'):<9} [dim]{escape(p.marketplace)}[/]"
        )
    drift = sum(1 for p in rows_list if not p.declared)
    if drift:
        console.print(
            f"  [yellow]⚠ {drift} undeclared plugin(s)[/] [dim]beyond the plugins.yaml allowlist "
            "— each ships always-on skill descriptions · prune: dfs agent setup claude --clean[/]"
        )


def _render_permissions(rows: Iterable[PermissionRow], home: Path) -> None:
    rows_list = list(rows)
    _ov_section("Permissions")
    if not rows_list:
        console.print("  [dim](none)[/]")
        return
    for p in rows_list:
        qty = (
            f"prefix_rules {p.prefix_rules}"
            if p.prefix_rules
            else f"allow {p.allow}  deny {p.deny}"
        )
        console.print(
            f"  [{_GOLD}]{escape(p.label):<26}[/] {qty:<22} {_path_link(p.source_path, home)}"
        )


def _confirmations(data: AgentOverview) -> dict[str, str]:
    """A verifiable one-line confirm per agent, derived from the overview data."""
    conf: dict[str, str] = {}
    for s in data.vendor_surfaces:
        if s.agent == "claude" and s.label == "skills" and s.quantity:
            conf["claude"] = f"{s.quantity} resolve via the Skill tool"
    conf["codex"] = f"{sum(1 for r in data.mcp if r.codex)} MCP enabled (codex mcp list)"
    conf["cursor"] = "GUI — Cursor → Settings → MCP / Rules"
    conf["gemini"] = "Antigravity (agy) — config in ~/.gemini, AGENTS.md instructions"
    conf["pi"] = "config in ~/.pi/agent (pi is interactive)"
    return conf


def _render_agent_gaps(data: AgentOverview, agent: str) -> None:
    """Per-vendor lines: closable gaps (we can deploy) vs not-globally-closable ones."""
    gaps = [r.capability for r in data.uniformity if r.cells.get(agent) == "gap"]
    local = [r.capability for r in data.uniformity if r.cells.get(agent) == "local"]
    if gaps:
        console.print(
            f"  [red]gaps[/]           [dim]{escape(', '.join(gaps))} "
            "— supported, deployable, not yet done[/]"
        )
    if local:
        console.print(
            f"  [yellow]not closable[/]   [dim]{escape(', '.join(local))} "
            "— supported only workspace-local/ext/beta[/]"
        )


def _render_one_agent_section(
    agent: str, surfaces: list[AgentSurface], data: AgentOverview, home: Path
) -> None:
    _ov_section(_VENDOR_HEADERS.get(agent, agent))
    if len(surfaces) == 1 and surfaces[0].status == "skipped":
        console.print(f"  [dim]·  {escape(surfaces[0].detail)}[/]")
        return
    for s in surfaces:
        glyph = _STATUS_GLYPH.get(s.status, "[dim]·[/]")
        console.print(
            f"  {glyph}  [{_GOLD}]{escape(s.label):<14}[/] "
            f"{escape(s.quantity):<12} {_path_link(s.path, home)}"
        )
    _render_agent_gaps(data, agent)
    confirm = _confirmations(data).get(agent)
    if confirm:
        console.print(f"  [dim]confirm[/]        [dim]{escape(confirm)}[/]")


def _render_agent_sections(data: AgentOverview, home: Path) -> None:
    for agent, group in groupby(data.vendor_surfaces, key=lambda s: s.agent):
        _render_one_agent_section(agent, list(group), data, home)


def _render_overview(data: AgentOverview, home: Path) -> None:
    """Render the dashboard: colocated matrices, plugins, then per-agent surfaces."""
    print_title(console, "agent", "overview")
    _render_capability_matrix(data.capabilities)
    _render_uniformity_matrix(data.uniformity)
    if (stale := data.fleet_doc_stale_days) is not None and stale > _FLEET_STALE_DAYS:
        console.print(
            f"  [yellow]⚠ agent-fleet.md last reviewed {stale}d ago[/] "
            "[dim]· re-check the landscape (new vendor features?)[/]"
        )
    _render_value_matrix("Skills & Rules", data.skills_rules)
    _render_plugins(data.plugins)
    _render_state_matrix("MCP servers", data.mcp, _MCP_AGENTS, "server")
    _render_state_matrix("Subagents", data.agents, _SUBAGENT_AGENTS, "name")
    _render_state_matrix("Hooks", data.hooks, _HOOK_AGENTS, "event")
    _render_permissions(data.permissions, home)
    _render_agent_sections(data, home)
    console.print()


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _render_setup_results(agent: str, results: list[StepResult]) -> None:
    """Print step results for one agent under its vendor header."""
    header = _VENDOR_HEADERS.get(agent, agent)
    console.print(f"\n[bold]── {header} ──[/]")
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
    prune: bool = typer.Option(
        False, "--prune", help="After deploying, delete retired skills so dirs mirror canonical."
    ),
) -> None:
    """Configure AI agent tooling (Claude Code, Cursor, Codex, Gemini, Pi)."""
    app_ctx = app_context(ctx)
    agents = [agent.value] if agent is not None else list(ALL_AGENTS)

    results = run_setup(app_ctx, agents=agents, clean=clean, reset_mcp=reset_mcp)
    for result in results:
        _render_setup_results(result.agent, result.steps)

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
    _render_overview(svc.overview(), app_ctx.home)


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
    _render_capability_matrix(capability_rows())
    print_section(console, "Receipts", "probe (on-machine) · source (documentary) per cell")
    for cap, agent, cell in receipts():
        proof = cell.test or cell.src
        kind = "probe" if cell.test else "src"
        console.print(
            f"  [{_GOLD}]{escape(cap):<18}[/] [dim]{escape(agent):<7}[/] "
            f"[{_CAP_GLYPH.get(cell.status, ('?', 'dim'))[1]}]{cell.status:<10}[/] "
            f"[dim]{kind}:[/] {escape(proof)}"
        )
    if verify:
        _verify_capability_probes(app_ctx.runner)


def _verify_capability_probes(runner: ProcessRunner) -> None:
    """Run each cell's probe and check it AGREES with the claimed status — the tether.

    A supported claim (yes/beta/ext) expects the probe to exit 0; a proven-absent
    claim (no) expects it to exit non-zero (the capability really isn't there). A
    mismatch means the matrix has drifted from reality.
    """
    print_section(console, "Verify", "probe agrees with claim · ✗ = matrix drifted from reality")
    agree = drift = skipped = 0
    for cap, agent, cell in receipts():
        if not cell.test:
            skipped += 1
            continue
        present = runner.run(("bash", "-lc", cell.test), check=False).exit_code == 0
        expect_present = cell.status in ("yes", "beta", "ext")
        ok = present == expect_present
        agree += ok
        drift += not ok
        mark = "[green]✓ agrees[/]" if ok else "[red]✗ DRIFT[/]"
        verdict = "present" if present else "absent"
        console.print(
            f"  {mark}  [dim]{escape(cap)}·{escape(agent)}[/] "
            f"claim={cell.status} probe={verdict}  [dim]{escape(cell.test[:46])}[/]"
        )
    console.print(f"\n  [dim]{agree} agree · {drift} DRIFT · {skipped} no-probe (source-only)[/]")


@agent_app.command()
def lint(ctx: typer.Context) -> None:
    """Validate .ai/skills/ and .ai/agents/ markdown files (was: verify skills)."""
    app_ctx = app_context(ctx)

    results = validate_skill_files(app_ctx.dotfiles_dir)

    print_title(console, "agent", "lint")
    for v in results:
        _render_validation(v)

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


_ORIGIN_STYLE: dict[str, str] = {
    "canonical": "green",
    "external": "cyan",
    "plugin": "magenta",
    "builtin": "blue",
    "retired": "red",
    "untracked": "yellow",
}

# Per-origin provenance + how-to-manage hint, shown in each section header so the
# row list needs no origin column. Plugins override this with their marketplace ref.
_ORIGIN_PROVENANCE: dict[str, str] = {
    "canonical": "this repo, ai/skills/ — edit directly",
    "external": "opt-in via external-skills.txt — npx skills add/remove",
    "plugin": "Claude Code plugin — manage via /plugin",
    "builtin": "vendor builtin (Cursor/Codex) — left untouched",
    "retired": "was ours, removed from canonical — dfs agent skills prune",
    "untracked": "manual/registry install — add to external-skills.txt or delete",
}

# `agent skills` (list) + `agent skills prune` — skills is its own sub-app.
skills_app = typer.Typer(help="List skills by origin, and prune retired ones.")


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(1, width - 1)] + "…"


def _order_by_origin(skills: list[SkillInfo]) -> list[SkillInfo]:
    """Group by origin (canonical → … → untracked, the _ORIGIN_STYLE order), then
    alphabetically by name within each origin. Unknown origins sort last."""
    rank = {origin: i for i, origin in enumerate(_ORIGIN_STYLE)}
    return sorted(skills, key=lambda s: (rank.get(s.origin, len(rank)), s.name))


def _origin_provenance(origin: str, group: list[SkillInfo]) -> str:
    """Provenance + management hint for an origin's section header. For plugins the
    marketplace ref is the real fingerprint, so surface the distinct ref(s)."""
    if origin == "plugin":
        refs = sorted({s.source for s in group if s.source})
        if refs:
            return f"{', '.join(refs)} — manage via /plugin"
    return _ORIGIN_PROVENANCE.get(origin, "unknown provenance")


def _render_skills(skills: list[SkillInfo]) -> None:
    # Per-origin sections (input is already grouped by _order_by_origin). The header
    # carries origin + provenance + count, so rows drop the now-redundant origin
    # column and hand that width to the description. Manual columns (not a Rich
    # Table) so a no-wrap description can't collapse the name column at narrow widths.
    name_w = min(34, max((len(s.name) for s in skills), default=8) + 1)
    desc_w = max(16, console.width - 5 - name_w)
    by_origin: dict[str, list[SkillInfo]] = {}
    for s in skills:
        by_origin.setdefault(s.origin, []).append(s)
    for origin, group in by_origin.items():
        color = _ORIGIN_STYLE.get(origin, "dim")
        console.print(
            f"\n  [bold {color}]{origin}[/] "
            f"[dim]· {escape(_origin_provenance(origin, group))} · {len(group)}[/]"
        )
        for s in group:
            desc = _clip(" ".join(s.description.split()), desc_w)
            console.print(
                f"    {escape(_clip(s.name, name_w).ljust(name_w))} [{_GOLD}]{escape(desc)}[/]"
            )


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
    items = _order_by_origin(items)
    counts: dict[str, int] = {}
    for s in items:
        counts[s.origin] = counts.get(s.origin, 0) + 1
    tally = "  ".join(
        f"[{_ORIGIN_STYLE[o]}]{o} {counts[o]}[/]" for o in _ORIGIN_STYLE if o in counts
    )
    console.print(f"  {len(items)} skills · {tally}")
    if hidden_builtin:
        console.print(f"  [dim]+ {hidden_builtin} vendor builtin hidden · --all to show[/]")
    console.print()
    _render_skills(items)


# (origin, glyph-color, glyph, section hint) — the order they render in.
_ORPHAN_BUCKETS: tuple[tuple[str, str, str, str], ...] = (
    ("retired", "red", "✗", "were ours, renamed/removed — safe to delete"),
    ("builtin", "blue", "·", "shipped by the vendor (Cursor/Codex) — left untouched"),
    ("untracked", "yellow", "?", "registry/manual installs — add to external-skills.txt to keep"),
)


def _render_orphans(orphans: list[SkillOrphan]) -> None:
    """Show retired / builtin / untracked orphans in labelled buckets."""
    for origin, color, glyph, hint in _ORPHAN_BUCKETS:
        group = [o for o in orphans if o.origin == origin]
        if not group:
            continue
        print_section(console, origin.capitalize(), hint)
        for o in group:
            console.print(f"  [{color}]{glyph}[/] [dim]{o.location}/[/]{o.name}")


def _render_collision_report(report: SkillCollisionReport) -> None:
    console.print(
        f"  [dim]{report.local_count} canonical skills · "
        f"{report.external_count} Pi-package skills scanned[/]"
    )
    if not report.collisions:
        print_status(console, "success", "No local/Pi-package skill collisions found")
        return
    by_domain: dict[str, list[SkillCollision]] = {}
    for collision in report.collisions:
        by_domain.setdefault(collision.domain, []).append(collision)
    for domain in sorted(by_domain):
        print_section(console, domain, "likely overlapping trigger/domain")
        for c in by_domain[domain]:
            glyph = "=" if c.kind == "same-name" else "~"
            console.print(
                f"  [yellow]{glyph}[/] [bold]{escape(c.local.name)}[/] "
                f"[dim]({escape(c.local.path)})[/]  ↔  "
                f"[{_GOLD}]{escape(c.external.name)}[/] "
                f"[dim]({escape(c.external.source)} · {escape(c.external.path)})[/]"
            )
            console.print(f"      [dim]{escape(c.reason)}[/]")


@skills_app.command("audit")
def skills_audit(ctx: typer.Context) -> None:
    """Audit likely trigger collisions between owned skills and Pi package skills."""
    app_ctx = app_context(ctx)
    print_title(console, "agent", "skills", "audit")
    _render_collision_report(collision_report(home=app_ctx.home, dotfiles_dir=app_ctx.dotfiles_dir))


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
    _render_orphans(orphans)
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
        console.print_json(data=_stats_json(report))
    else:
        _render_stats(report)


def _render_stats(report: SkillUsageReport) -> None:
    days = (report.now - report.since).days
    print_title(console, "agent", "stats")
    console.print(
        f"[bold]Skill Usage[/]  [dim]{report.projects} projects · "
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
    console.print("[bold]Leaderboard[/]")
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
    console.print("[bold]⚠ Trigger health[/] [dim]— reached mostly by typing the slash command[/]")
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
        f"[bold]🪦 Dead[/] [dim]— deployed, 0 fires in window ({len(dead)} candidates)[/]"
    )
    console.print("  [dim]" + " · ".join(escape(d) for d in dead) + "[/]")


def _render_sequences(sequences: tuple[tuple[tuple[str, str], int], ...]) -> None:
    if not sequences:
        return
    console.print()
    console.print("[bold]🔗 Sequences[/] [dim]— skills that chain[/]")
    for (first, second), count in sequences[:8]:
        console.print(f"  [dim]{escape(first)} → {escape(second)}[/]  ({count}x)")


def _render_vendors(counts: tuple[tuple[str, int], ...]) -> None:
    console.print()
    parts = "  ".join(f"{escape(v)} {n}" for v, n in counts) or "[dim](none)[/]"
    console.print(f"[bold]Vendors[/]  {parts}  [dim]· Cursor — (GUI, no logs)[/]")
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
    _render_health(result)


def _render_health(r: HealthBootstrap) -> None:
    print_title(console, "agent", "health")
    console.print(
        f"[bold]Code-health backbone[/]  [dim]scope: {escape(r.scope)} · "
        f"lang: {escape(r.language)}[/]"
    )
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
    console.print("[bold]Hotspots[/] [dim]— churn*LOC; spend refactor effort here first[/]")
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
    """The code-health backbone: doctrine hierarchy + live ratchet floor + symptom→rite router."""
    app_ctx = app_context(ctx)
    print_title(console, "agent", "catechism")
    _render_doctrine(DOCTRINE)
    _render_scope_health(read_scope_health(app_ctx.dotfiles_dir))
    _render_catechism(CATECHISM)
    console.print(
        "\n[dim]The doctrine: CANON.md · the theory: code-health-portfolio.md · "
        "verify live: just check (ratchet-check.sh)[/]"
    )


def _render_doctrine(layers: tuple[DoctrineLayer, ...]) -> None:
    _ov_section("Doctrine", "the backbone — outermost → innermost")
    width = max((len(layer.name) for layer in layers), default=8)
    for layer in layers:
        console.print(
            f"  [{_GOLD}]{escape(layer.name):<{width}}[/]  {escape(layer.role)}\n"
            f"  {' ' * width}  [dim]{escape(layer.doc)}[/]"
        )


def _render_scope_health(scopes: list[ScopeHealth]) -> None:
    _ov_section("Health baselines", "the ratchet floor — every ceiling may only DECREASE")
    if not scopes:
        console.print("  [dim](no docs/health/<scope>/baselines.json yet)[/]")
        return
    for s in scopes:
        supp = " · ".join(f"{k} {v}" for k, v in s.suppressions.items())
        cx = f"≤{s.complexity_max}"
        cx += " ✓" if s.complexity_over == 0 else f" [red]({s.complexity_over} over)[/]"
        console.print(
            f"  [{_GOLD}]{escape(s.scope)}[/]  [dim]{s.loc} LOC · complexity {cx} · "
            f"updated {escape(s.updated)}[/]"
        )
        console.print(f"    [dim]suppressions:[/] {escape(supp)}")


def _render_catechism(entries: tuple[CatechismEntry, ...]) -> None:
    _ov_section("Router", "symptom → the rite to reach for · front door: code-health")
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("You want to…", style="dim", max_width=48)
    tbl.add_column("Reach for")
    tbl.add_column("Tier · kind", style="dim")
    for e in entries:
        tbl.add_row(escape(e.symptom), f"[bold]{escape(e.rite)}[/]", escape(e.tier))
    console.print(tbl)


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
    console.print("[bold]Gemini chunks[/] (target: ~1500 chars each)\n")
    for chunk in chunks:
        console.print(f"  {chunk.char_count:>4} chars  {escape(chunk.name)}")


def _gemini_step(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print(
        "[bold]Interactive mode[/]: copy each chunk, paste into Gemini Saved Info,"
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
    console.print(f"[bold]Loading {len(chunks)} chunks into clipboard history (for Flycut)…[/]")
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


agent_app.add_typer(skills_app, name="skills")
agent_app.add_typer(web_app, name="web")
