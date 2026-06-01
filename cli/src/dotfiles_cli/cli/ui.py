"""Presentation helpers for the CLI: render core StepResults to a Rich console."""

from collections.abc import Iterable

from rich.console import Console

from dotfiles_cli.core.models import ConnectionInfo, StepLevel, StepResult

_GLYPH: dict[StepLevel, str] = {
    "success": "[green]✓[/]",
    "warn": "[yellow]⚠[/]",
    "error": "[red]✗[/]",
    "info": "[dim]•[/]",
}


def render_steps(console: Console, steps: Iterable[StepResult]) -> None:
    for step in steps:
        console.print(f"  {_GLYPH[step.level]} {step.message}")


def has_errors(steps: Iterable[StepResult]) -> bool:
    return any(step.level == "error" for step in steps)


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
