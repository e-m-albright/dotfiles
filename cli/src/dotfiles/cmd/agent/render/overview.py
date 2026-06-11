"""Overview/matrix render helpers for `dotfiles agent overview`."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import groupby
from pathlib import Path

from rich.markup import escape

from dotfiles.agent import OVERVIEW_AGENTS, OVERVIEW_COLS, VENDORS
from dotfiles.cmd.agent.capability_matrix import (
    FLEET_STALE_DAYS,
    CapabilityRow,
    Cell,
)
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentPresenceRow,
    AgentSurface,
    PermissionRow,
    PluginRow,
    UniformityRow,
    ValueRow,
)
from dotfiles.console import console, print_title

# Derived from the single VENDORS registry in dotfiles.agent — don't re-list here.
_VENDOR_HEADERS = {v.name: v.display_name for v in VENDORS}

# Brand gold for soft attribute/value text (replaces the hard-to-read dim grey).
GOLD = "#cdbf80"
# Fixed agent column order for every matrix.
_AGENT_COLS: tuple[str, ...] = OVERVIEW_AGENTS
_COL_W = 8
_LABEL_W = 24
# Which agents each surface applies to; others render "·" (n/a), never "✗".
# Derived from the registry's Deploy stances — never hand-listed — so the matrices
# can't drift from the vendor pages / verify, which read the same stances. The
# hook-intents matrix applies only where the deploy IS the shared-intent wiring
# (pi's hooks ride an extension, not these scripts). MCP intent comes from
# mcp-servers.json targets, carried on the overview data (data.mcp_agents).
_HOOK_AGENTS = {v.name for v in VENDORS if (d := v.deploy("hooks")) and d.proof == "hook-intents"}
_SUBAGENT_AGENTS = {v.name for v in VENDORS if v.deploy("subagents")}
_STATUS_GLYPH = {
    "present": "[green]✓[/]",
    "empty": "[yellow]○[/]",
    "missing": "[red]✗[/]",
    "skipped": "[dim]·[/]",
}


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


def _render_state_matrix(title: str, rows: Iterable[AgentPresenceRow], applies: set[str]) -> None:
    rows_list = list(rows)
    if not rows_list:
        _ov_section(title)
        console.print("  [dim](none)[/]")
        return
    _matrix_header(title)
    for row in rows_list:
        cells = "".join(
            _state_cell(bool(row.cells.get(a, False)), a in applies) for a in _AGENT_COLS
        )
        console.print(f"  {escape(row.label):<{_LABEL_W}}{cells}")


CAP_GLYPH: dict[str, tuple[str, str]] = {
    "yes": ("✓", "green"),  # supported (GA) — receipt in the cell
    "beta": ("◐", "yellow"),  # preview / partial / auto-only
    "ext": ("⊕", "cyan"),  # supported only via an extension (Pi)
    "no": ("✗", "red"),  # proven absent (with evidence)
    "unverified": ("?", "dim"),  # no first-party source AND not locally probeable
}


def _capability_cell(cell: Cell) -> str:
    glyph, color = CAP_GLYPH.get(cell.status, ("?", "dim"))
    return f"[{color}]{glyph.center(_COL_W)}[/]"


def render_capability_matrix(rows: Iterable[CapabilityRow]) -> None:
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
        cells = "".join(f"[{GOLD}]{row.cells.get(a, '—').center(_COL_W)}[/]" for a in _AGENT_COLS)
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
            f"  {mark} [{GOLD}]{escape(p.name):<26}[/] "
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
            f"  [{GOLD}]{escape(p.label):<26}[/] {qty:<22} {_path_link(p.source_path, home)}"
        )


def _confirmations(data: AgentOverview) -> dict[str, str]:
    """A verifiable one-line confirm per agent, derived from the overview data."""
    conf: dict[str, str] = {}
    for s in data.vendor_surfaces:
        if s.agent == "claude" and s.label == "skills" and s.quantity:
            conf["claude"] = f"{s.quantity} resolve via the Skill tool"
    conf["codex"] = (
        f"{sum(1 for r in data.mcp if r.cells.get('codex'))} MCP enabled (codex mcp list)"
    )
    conf["cursor"] = "GUI — Cursor → Settings → MCP / Rules"
    conf["gemini"] = "Antigravity (agy) — config in ~/.gemini, AGENTS.md instructions"
    conf["pi"] = "config in ~/.pi/agent (pi is interactive)"
    conf["hermes"] = (
        "skills in ~/.hermes/skills; rules via project AGENTS.md (hermes is interactive)"
    )
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
        # Path-backed rows link the path; intentional non-deploys show their reason.
        tail = _path_link(s.path, home) if s.path else f"[dim]{escape(s.detail)}[/dim]"
        console.print(
            f"  {glyph}  [{GOLD}]{escape(s.label):<14}[/] {escape(s.quantity):<12} {tail}"
        )
    _render_agent_gaps(data, agent)
    confirm = _confirmations(data).get(agent)
    if confirm:
        console.print(f"  [dim]confirm[/]        [dim]{escape(confirm)}[/]")


def _render_agent_sections(data: AgentOverview, home: Path) -> None:
    for agent, group in groupby(data.vendor_surfaces, key=lambda s: s.agent):
        _render_one_agent_section(agent, list(group), data, home)


def render_overview(data: AgentOverview, home: Path) -> None:
    """Render the dashboard: colocated matrices, plugins, then per-agent surfaces."""
    print_title(console, "agent", "overview")
    render_capability_matrix(data.capabilities)
    _render_uniformity_matrix(data.uniformity)
    if (stale := data.fleet_doc_stale_days) is not None and stale > FLEET_STALE_DAYS:
        console.print(
            f"  [yellow]⚠ agent-fleet.md last reviewed {stale}d ago[/] "
            "[dim]· re-check the landscape (new vendor features?)[/]"
        )
    _render_value_matrix("Skills & Rules", data.skills_rules)
    _render_plugins(data.plugins)
    _render_state_matrix("MCP servers", data.mcp, set(data.mcp_agents))
    _render_state_matrix("Subagents", data.agents, _SUBAGENT_AGENTS)
    _render_state_matrix("Hooks", data.hooks, _HOOK_AGENTS)
    _render_permissions(data.permissions, home)
    _render_agent_sections(data, home)
    console.print()
