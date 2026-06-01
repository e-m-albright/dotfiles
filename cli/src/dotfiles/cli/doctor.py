"""`dotfiles doctor [--fix]` command — renders grouped CheckResults."""

from __future__ import annotations

from itertools import groupby
from typing import Annotated

import typer

from dotfiles.cli.context import AppContext
from dotfiles.console import console
from dotfiles.core.doctor import DoctorService
from dotfiles.core.models import CheckResult

_GLYPH: dict[str, str] = {
    "ok": "[green]✓[/]",
    "missing": "[red]✗[/]",
    "warn": "[yellow]○[/]",
    "fixed": "[green]→[/]",
}


def render_checks(results: list[CheckResult]) -> None:
    """Print results grouped by section to the shared console."""
    for section, group in groupby(results, key=lambda r: r.section):
        console.print(f"\n[bold blue]{section}[/]")
        for r in group:
            glyph = _GLYPH.get(r.status, "?")
            line = f"  {glyph} {r.name}"
            if r.detail:
                line += f"  [dim]{r.detail}[/]"
            if r.hint and r.status in ("missing", "warn"):
                line += f"  [yellow]{r.hint}[/]"
            console.print(line)


def doctor_command(
    ctx: typer.Context,
    fix: Annotated[bool, typer.Option("--fix", help="Attempt to repair missing config.")] = False,
) -> None:
    """Check all tools and configuration are installed."""
    app_ctx: AppContext = ctx.obj
    svc = DoctorService(
        runner=app_ctx.runner,
        fs=app_ctx.fs,
        home=app_ctx.home,
        dotfiles_dir=app_ctx.dotfiles_dir,
        fix=fix,
    )
    results = svc.run()
    render_checks(results)
    console.print()

    failures = [r for r in results if r.is_failure]
    if fix:
        console.print("[dim]Run 'dotfiles agent setup' to redeploy agent configs.[/]")

    if failures:
        console.print(
            "[yellow]→ Some tools are missing. Run install.sh or install individually.[/]"
        )
        raise typer.Exit(1)
    else:
        console.print("[green]✓ All checks passed![/]")
