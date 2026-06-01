"""`dotfiles agent` commands: dashboard overview + skill/agent lint."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import groupby

import typer
from rich.markup import escape
from rich.table import Table

from dotfiles.cli.context import AppContext
from dotfiles.console import console
from dotfiles.core.agent_overview import AgentOverviewService
from dotfiles.core.models import (
    AgentOverview,
    AgentRow,
    FileValidation,
    HookRow,
    McpRow,
    PermissionRow,
    VendorSurface,
)
from dotfiles.core.skills import SkillValidateService

agent_app = typer.Typer(help="Agentic setup: overview dashboard and skill/agent lint.")

# ---------------------------------------------------------------------------
# Glyph / render helpers (moved from cli/verify.py)
# ---------------------------------------------------------------------------

_VENDOR_HEADERS = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
    "gemini": "Gemini",
    "pi": "Pi",
}

_CLI_CONFIRMATION = {
    "claude": "CLI confirmation: skills auto-listed in every Claude Code session via Skill tool",
    "cursor": "CLI confirmation: GUI only — Cursor → Settings → MCP / Rules",
    "codex": "CLI confirmation: 'codex' (interactive) — no list-skills subcommand",
    "gemini": "CLI confirmation: 'gemini' (interactive)",
    "pi": "CLI confirmation: 'pi' (interactive, LM Studio local-first)",
}

_BOOL_GLYPH = {True: "[green]✓[/]", False: "[dim]—[/]"}


def _render_surface(surface: VendorSurface) -> None:
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


def _render_agents(rows: Iterable[AgentRow]) -> None:
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


def _render_vendor_surfaces(surfaces: Iterable[VendorSurface]) -> None:
    console.print()
    console.print("[bold blue]Vendor Surfaces[/]")
    first = True
    for vendor, group in groupby(surfaces, key=lambda s: s.vendor):
        if not first:
            console.print()
        first = False
        header = _VENDOR_HEADERS.get(vendor, vendor)
        console.print(f"[blue]══ {header} ══[/]")
        vendor_list = list(group)
        for surface in vendor_list:
            _render_surface(surface)
        not_skipped = not (len(vendor_list) == 1 and vendor_list[0].status == "skipped")
        if not_skipped and vendor in _CLI_CONFIRMATION:
            console.print(f"  [dim]{_CLI_CONFIRMATION[vendor]}[/]")


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
# Commands
# ---------------------------------------------------------------------------


@agent_app.command()
def overview(ctx: typer.Context) -> None:
    """Show the full agentic setup dashboard (MCP, hooks, skills, subagents, rules, permissions)."""
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)

    svc = AgentOverviewService(
        fs=app_ctx.fs,
        runner=app_ctx.runner,
        dotfiles_dir=app_ctx.dotfiles_dir,
        home=app_ctx.home,
    )
    _render_overview(svc.overview())


@agent_app.command()
def lint(ctx: typer.Context) -> None:
    """Validate .ai/skills/ and .ai/agents/ markdown files (was: verify skills)."""
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)

    service = SkillValidateService(fs=app_ctx.fs, dotfiles_dir=app_ctx.dotfiles_dir)
    results = service.validate()

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
