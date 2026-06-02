"""Shared Rich consoles + the step-result rendering helpers used by every command."""

from collections.abc import Iterable

import typer
from rich.console import Console
from rich.markup import escape

from dotfiles.result import StepLevel, StepResult

# NOTE: tests that capture output should inject their own Console(file=StringIO());
# do not rely on patching these globals.
console = Console()
err_console = Console(stderr=True)

_GLYPH: dict[StepLevel, str] = {
    "success": "[green]✓[/]",
    "warn": "[yellow]⚠[/]",
    "error": "[red]✗[/]",
    "info": "[dim]•[/]",
}


def render_steps(console: Console, steps: Iterable[StepResult]) -> None:
    for step in steps:
        line = f"  {_GLYPH[step.level]} {escape(step.message)}"
        if step.details:
            line += f" [dim]{escape(step.details)}[/]"
        console.print(line)


def has_errors(steps: Iterable[StepResult]) -> bool:
    return any(step.level == "error" for step in steps)


def render_and_exit(console: Console, steps: list[StepResult], *, code: int = 1) -> None:
    """Render *steps*, then exit non-zero if any step is an error."""
    render_steps(console, steps)
    if has_errors(steps):
        raise typer.Exit(code=code)
