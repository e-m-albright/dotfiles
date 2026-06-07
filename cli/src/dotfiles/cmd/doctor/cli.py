"""`dotfiles doctor [--fix]` command — renders grouped CheckResults."""

from __future__ import annotations

from itertools import groupby
from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.cmd.doctor.models import CheckResult
from dotfiles.cmd.doctor.service import DoctorService
from dotfiles.console import console

_GLYPH: dict[str, str] = {
    "ok": "[green]✓[/]",
    "missing": "[red]✗[/]",
    "warn": "[yellow]○[/]",
    "fixed": "[green]→[/]",
}


def _check_line(r: CheckResult) -> str:
    """One rendered check row: glyph + name + optional detail + optional hint."""
    line = f"  {_GLYPH.get(r.status, '?')} {r.name}"
    if r.detail:
        line += f"  [dim]{r.detail}[/]"
    if r.hint and r.status in ("missing", "warn"):
        line += f"  [yellow]{r.hint}[/]"
    return line


def render_checks(results: list[CheckResult]) -> None:
    """Print results grouped by section to the shared console."""
    for section, group in groupby(results, key=lambda r: r.section):
        console.print(f"\n[bold blue]{section}[/]")
        for r in group:
            console.print(_check_line(r))


def doctor_command(
    ctx: typer.Context,
    fix: Annotated[bool, typer.Option("--fix", help="Attempt to repair missing config.")] = False,
) -> None:
    """Check all tools and configuration are installed."""
    app_ctx = app_context(ctx)
    svc = DoctorService(
        runner=app_ctx.runner,
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
