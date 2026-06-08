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


# --- House style: shared visual language across commands -------------------
#
# Three primitives give every command the same literal + visual grammar: a
# compact titled rule, glyph status lines (with an optional indented sub-line),
# and an aligned label column. Keep lines short — a title rule caps at
# _SECTION_WIDTH, values that must stay copyable (long commands) opt into
# soft_wrap instead of wrapping mid-token.

_SECTION_WIDTH = 42
_FIELD_WIDTH = 10


def print_title(console: Console, title: str) -> None:
    """A compact left-titled rule: ``── Title ───────``, capped at _SECTION_WIDTH."""
    lead = f"── {title} "
    dashes = "─" * max(3, _SECTION_WIDTH - len(lead))
    console.print(f"\n[bold cyan]{escape(lead)}{dashes}[/]")


def print_status(console: Console, level: StepLevel, message: str, sub: str | None = None) -> None:
    """A glyph status line, with an optional dimmed continuation on its own line."""
    console.print(f"  {_GLYPH[level]} {escape(message)}")
    if sub:
        console.print(f"    [dim]{escape(sub)}[/]")


def print_field(console: Console, label: str, value: str, *, soft_wrap: bool = False) -> None:
    """An aligned ``label   value`` row (dim label). soft_wrap keeps long values copyable."""
    console.print(f"  [dim]{label:<{_FIELD_WIDTH}}[/] {escape(value)}", soft_wrap=soft_wrap)


def has_errors(steps: Iterable[StepResult]) -> bool:
    return any(step.level == "error" for step in steps)


def render_and_exit(console: Console, steps: list[StepResult], *, code: int = 1) -> None:
    """Render *steps*, then exit non-zero if any step is an error."""
    render_steps(console, steps)
    if has_errors(steps):
        raise typer.Exit(code=code)
