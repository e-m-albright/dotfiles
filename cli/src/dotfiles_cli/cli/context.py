"""Composition root: wire real adapters into an AppContext stored on the Typer Context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

from dataclasses import dataclass
from pathlib import Path

from dotfiles_cli.adapters.clock import SystemClock
from dotfiles_cli.adapters.filesystem import LocalFileSystem
from dotfiles_cli.adapters.process import SubprocessRunner
from dotfiles_cli.core.ports import Clock, FileSystem, ProcessRunner
from dotfiles_cli.core.settings import Settings


@dataclass(frozen=True)
class AppContext:
    """Everything a command needs: ports, settings, environment facts."""

    runner: ProcessRunner
    fs: FileSystem
    clock: Clock
    settings: Settings
    interactive: bool
    home: Path


def build_real_context(*, interactive: bool) -> AppContext:
    return AppContext(
        runner=SubprocessRunner(),
        fs=LocalFileSystem(),
        clock=SystemClock(),
        settings=Settings(),
        interactive=interactive,
        home=Path.home(),
    )
