"""Composition root: wire real adapters into an AppContext stored on the Typer Context.

Tests inject a fake AppContext via `runner.invoke(app, args, obj=fake_ctx)`.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import typer

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
    state_dir: Path = _REPO_ROOT / ".local-state"  # overridden by build_real_context
    # Feature flags enabled via the environment (AI/PRODUCTIVITY/SOCIAL); read in
    # the composition root, never via os.environ inside a command.
    feature_flags: frozenset[str] = frozenset({"ai", "productivity", "social"})


def app_context(ctx: typer.Context) -> AppContext:
    """Return the AppContext stored on the Typer context by the composition root.

    The single accessor every command uses to unwrap ``ctx.obj`` — replaces the
    per-module ``_ctx`` helpers and the inline ``assert isinstance`` unwraps.
    """
    obj = ctx.obj
    assert isinstance(obj, AppContext)
    return obj


def _env_feature_flags() -> frozenset[str]:
    """Flags enabled via env vars (AI/PRODUCTIVITY/SOCIAL); on unless set to "0"."""
    env_names = {"ai": "AI", "productivity": "PRODUCTIVITY", "social": "SOCIAL"}
    return frozenset(flag for flag, env in env_names.items() if os.environ.get(env, "1") != "0")


def build_real_context(*, interactive: bool) -> AppContext:
    dotfiles_dir = Path(os.environ["DOTFILES_DIR"]) if "DOTFILES_DIR" in os.environ else _REPO_ROOT
    home = Path.home()
    xdg_state = os.environ.get("XDG_STATE_HOME")
    state_root = Path(xdg_state) if xdg_state else home / ".local" / "state"
    return AppContext(
        runner=SubprocessRunner(),
        settings=Settings(),
        interactive=interactive,
        home=home,
        launcher=FzfExecLauncher(),
        http=UrllibHttpClient(),
        llm_settings=LlmSettings(),
        dotfiles_dir=dotfiles_dir,
        state_dir=state_root / "dotfiles",
        feature_flags=_env_feature_flags(),
    )
