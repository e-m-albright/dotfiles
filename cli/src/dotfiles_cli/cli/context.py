"""Composition root: wire real adapters into an AppContext stored on the Typer Context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotfiles_cli.adapters.clock import SystemClock
from dotfiles_cli.adapters.filesystem import LocalFileSystem
from dotfiles_cli.adapters.launcher import FzfExecLauncher
from dotfiles_cli.adapters.process import SubprocessRunner
from dotfiles_cli.core.ports import Clock, FileSystem, ProcessRunner
from dotfiles_cli.core.sessions import SessionLauncher
from dotfiles_cli.core.settings import Settings

# Repo root: cli/src/dotfiles_cli/cli/context.py → parents[4] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class AppContext:
    """Everything a command needs: ports, settings, environment facts."""

    runner: ProcessRunner
    fs: FileSystem
    clock: Clock
    settings: Settings
    interactive: bool
    home: Path
    launcher: SessionLauncher
    dotfiles_dir: Path = _REPO_ROOT


def build_real_context(*, interactive: bool) -> AppContext:
    dotfiles_dir = Path(os.environ["DOTFILES_DIR"]) if "DOTFILES_DIR" in os.environ else _REPO_ROOT
    return AppContext(
        runner=SubprocessRunner(),
        fs=LocalFileSystem(),
        clock=SystemClock(),
        settings=Settings(),
        interactive=interactive,
        home=Path.home(),
        launcher=FzfExecLauncher(),
        dotfiles_dir=dotfiles_dir,
    )
