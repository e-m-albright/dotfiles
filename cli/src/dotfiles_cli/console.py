"""Shared Rich consoles for stdout and stderr."""

from rich.console import Console

console = Console()
err_console = Console(stderr=True)
