"""Composition root: wire real adapters into an AppContext stored on the Typer Context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotfiles.adapters.http import UrllibHttpClient
from dotfiles.adapters.launcher import FzfExecLauncher
from dotfiles.adapters.process import SubprocessRunner
from dotfiles.core.ports import HttpClient, ProcessRunner
from dotfiles.core.sessions import SessionLauncher
from dotfiles.core.settings import LlmSettings, Settings

# Repo root: cli/src/dotfiles/cli/context.py → parents[4] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class AppContext:
    """Everything a command needs: ports, settings, environment facts."""

    runner: ProcessRunner
    settings: Settings
    interactive: bool
    home: Path
    launcher: SessionLauncher
    http: HttpClient = field(default_factory=UrllibHttpClient)
    llm_settings: LlmSettings = field(default_factory=LlmSettings)
    dotfiles_dir: Path = _REPO_ROOT


def build_real_context(*, interactive: bool) -> AppContext:
    dotfiles_dir = Path(os.environ["DOTFILES_DIR"]) if "DOTFILES_DIR" in os.environ else _REPO_ROOT
    return AppContext(
        runner=SubprocessRunner(),
        settings=Settings(),
        interactive=interactive,
        home=Path.home(),
        launcher=FzfExecLauncher(),
        http=UrllibHttpClient(),
        llm_settings=LlmSettings(),
        dotfiles_dir=dotfiles_dir,
    )
