"""`dotfiles agent` commands: dashboard overview + skill/agent lint + setup."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from itertools import groupby

import typer
from rich.markup import escape
from rich.table import Table

from dotfiles.app.context import app_context
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentSurface,
    AgentVerify,
    FileValidation,
    HookRow,
    McpRow,
    PermissionRow,
    SubagentRow,
)
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.cmd.agent.setup import ALL_AGENTS, run_setup
from dotfiles.cmd.agent.skill_health import SkillHealthService
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
