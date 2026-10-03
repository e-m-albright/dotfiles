"""Runtime context contract stored on the Typer context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

from dataclasses import dataclass
from pathlib import Path

import typer

from dotfiles.ports import KeychainStore, ProcessRunner

# Repo root: cli/src/dotfiles/app/context.py → parents[4] = repo root
REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class AppContext:
    """Runtime ports and host paths shared by commands."""

    runner: ProcessRunner
    keychain: KeychainStore
    home: Path
    dotfiles_dir: Path = REPO_ROOT


def app_context(ctx: typer.Context) -> AppContext:
    """Return the AppContext stored on the Typer context by the composition root.

    The single accessor every command uses to unwrap ``ctx.obj`` — replaces the
    per-module ``_ctx`` helpers and the inline ``assert isinstance`` unwraps.
    """
    obj = ctx.obj
    assert isinstance(obj, AppContext)
    return obj
