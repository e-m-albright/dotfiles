"""`dotfiles doctor [--fix]` command — renders grouped CheckResults."""

from __future__ import annotations

from itertools import groupby
from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.cmd.doctor.models import CheckResult
from dotfiles.cmd.doctor.service import DoctorService
from dotfiles.console import console, print_section, print_status, print_title

_GLYPH: dict[str, str] = {
    "ok": "[green]✓[/]",
    "missing": "[red]✗[/]",
    "warn": "[yellow]⚠[/]",
    "fixed": "[green]→[/]",
}


_NAME_WIDTH = 14


def _check_line(r: CheckResult) -> str:
    """One rendered check row: glyph + name + optional detail + optional hint."""
    glyph = _GLYPH.get(r.status, "?")
    show_hint = bool(r.hint) and r.status in ("missing", "warn")
    if not r.detail and not show_hint:
        return f"  {glyph} {r.name}"
    line = f"  {glyph} {r.name:<{_NAME_WIDTH}}"
    if r.detail:
        line += f" [dim]{r.detail}[/]"
    if show_hint:
        line += f"  [yellow]{r.hint}[/]"
    return line


def render_checks(results: list[CheckResult]) -> None:
    """Print results grouped by section to the shared console."""
    for section, group in groupby(results, key=lambda r: r.section):
        print_section(console, section)
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
    print_title(console, "doctor", "checks")
    render_checks(results)
    console.print()

    failures = [r for r in results if r.is_failure]
    warnings = [r for r in results if r.status == "warn"]
    if fix:
        console.print("  [dim]Run 'workbench sync' to reconcile agent configs.[/]")

    if failures:
        print_status(console, "warn", "Some tools are missing — run install.sh or install each.")
        raise typer.Exit(1)
    if warnings:
        print_status(console, "warn", f"Checks completed with {len(warnings)} warning(s).")
        return
    print_status(console, "success", "All checks passed!")
