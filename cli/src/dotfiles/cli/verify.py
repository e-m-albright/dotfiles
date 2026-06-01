"""`dotfiles verify` commands: surface-level path checks for all vendor agents."""

from itertools import groupby

import typer

from dotfiles.cli.context import AppContext
from dotfiles.console import console
from dotfiles.core.models import FileValidation, VendorSurface
from dotfiles.core.skills import SkillValidateService
from dotfiles.core.verify import VendorVerifyService

verify_app = typer.Typer(help="Verify vendor agent surfaces (skills, MCP, hooks, etc.).")

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
    console.print(f"  {glyph} [dim]{surface.label:<25}[/] [dim]{surface.detail}[/]")


@verify_app.command()
def vendors(ctx: typer.Context) -> None:
    """Check each vendor's surface paths (skills, subagents, MCP, hooks, etc.)."""
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)

    service = VendorVerifyService(
        fs=app_ctx.fs,
        home=app_ctx.home,
        dotfiles_dir=app_ctx.dotfiles_dir,
    )

    surfaces = service.vendors()

    first = True
    for vendor, group in groupby(surfaces, key=lambda s: s.vendor):
        if not first:
            console.print()
        first = False

        header = _VENDOR_HEADERS.get(vendor, vendor)
        console.print(f"[blue]══ {header} ══[/]")

        vendor_surfaces = list(group)
        for surface in vendor_surfaces:
            _render_surface(surface)

        # Print CLI confirmation line — but only if not a single skipped entry
        not_skipped = not (len(vendor_surfaces) == 1 and vendor_surfaces[0].status == "skipped")
        if not_skipped and vendor in _CLI_CONFIRMATION:
            console.print(f"  [dim]{_CLI_CONFIRMATION[vendor]}[/]")

    console.print()
    console.print("[dim]── Summary ──[/]")
    console.print(
        "Skills deploy via the public [dim]npx skills[/] CLI"
        " to claude (~/.claude/skills/) and codex (~/.agents/skills/)."
    )
    console.print(
        "Rules are baked into each vendor's global file"
        " (Claude reads [dim]~/.claude/rules/*.md[/] natively)."
    )
    console.print("Verification depth varies — see CLI-confirmation lines above.")
    console.print("To deploy or refresh:  [dim]dotfiles agent setup[/]")


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


@verify_app.command()
def skills(ctx: typer.Context) -> None:
    """Validate .ai/skills/ and .ai/agents/ markdown files."""
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
