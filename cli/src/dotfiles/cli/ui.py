"""Presentation helpers for the CLI: render core StepResults to a Rich console."""

from collections.abc import Iterable

import typer
from rich.console import Console
from rich.markup import escape

from dotfiles.core.models import ConnectionInfo, StepLevel, StepResult

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
    """Render *steps*, then exit non-zero if any step is an error.

    The shared tail for commands that print a result list and fail the process
    when something went wrong.
    """
    render_steps(console, steps)
    if has_errors(steps):
        raise typer.Exit(code=code)


def render_connection_info(console: Console, info: ConnectionInfo) -> None:
    console.print("\n[bold]Termius setup[/]")
    console.print(f"  Host: {info.host}")
    if info.tailnet_ip:
        console.print(f"  Tailscale IP: {info.tailnet_ip}")
    else:
        console.print(
            "  [yellow]⚠[/] Tailscale does not look connected. "
            "Start Tailscale before connecting from your phone"
        )
    console.print(f"  Username: {info.user}")
    console.print("  Protocol: Mosh")
    console.print("\n[bold]Paste into Termius as the Mosh command:[/]")
    console.print(info.mosh_command, soft_wrap=True)
    console.print("\n[dim]Or connect and pick a live session:[/]")
    picker_cmd = info.mosh_command.replace(info.startup_command, "dotfiles sesh")
    console.print(picker_cmd, soft_wrap=True)
