"""`dotfiles verify` commands: surface-level path checks for all vendor agents."""

from itertools import groupby

import typer

from dotfiles_cli.cli.context import AppContext
from dotfiles_cli.console import console
from dotfiles_cli.core.models import VendorSurface
from dotfiles_cli.core.verify import VendorVerifyService

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
