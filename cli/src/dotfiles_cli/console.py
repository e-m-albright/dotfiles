"""Shared Rich consoles for stdout and stderr."""

from rich.console import Console

# NOTE: tests that capture output should inject their own Console(file=StringIO());
# do not rely on patching these globals.
console = Console()
err_console = Console(stderr=True)
