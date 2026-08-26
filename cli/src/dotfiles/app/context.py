"""Composition root: wire real adapters into an AppContext stored on the Typer Context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import typer

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.adapters.process import SubprocessRunner

# Repo root: cli/src/dotfiles/app/context.py → parents[4] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class AppContext:
    """Runtime ports and host paths shared by commands."""

    runner: ProcessRunner
    home: Path
    dotfiles_dir: Path = _REPO_ROOT


def app_context(ctx: typer.Context) -> AppContext:
    """Return the AppContext stored on the Typer context by the composition root.

    The single accessor every command uses to unwrap ``ctx.obj`` — replaces the
    per-module ``_ctx`` helpers and the inline ``assert isinstance`` unwraps.
    """
    obj = ctx.obj
    assert isinstance(obj, AppContext)
    return obj


def build_real_context() -> AppContext:
    dotfiles_dir = Path(os.environ["DOTFILES_DIR"]) if "DOTFILES_DIR" in os.environ else _REPO_ROOT
    return AppContext(
        runner=SubprocessRunner(),
        home=Path.home(),
        dotfiles_dir=dotfiles_dir,
    )
