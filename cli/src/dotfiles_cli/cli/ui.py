"""Presentation helpers for the CLI: render core StepResults to a Rich console."""

from collections.abc import Iterable

from rich.console import Console

from dotfiles_cli.core.models import StepLevel, StepResult

_GLYPH: dict[StepLevel, str] = {
    "success": "[green]✓[/]",
    "warn": "[yellow]⚠[/]",
    "error": "[red]✗[/]",
    "info": "[dim]•[/]",
}


def render_steps(console: Console, steps: Iterable[StepResult]) -> None:
    for step in steps:
        console.print(f"  {_GLYPH[step.level]} {step.message}")
