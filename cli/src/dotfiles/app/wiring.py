"""Construct the runtime context with concrete host adapters."""

import os
from pathlib import Path

from dotfiles.adapters.keychain import MacOSKeychainStore
from dotfiles.adapters.process import SubprocessRunner
from dotfiles.app.context import REPO_ROOT, AppContext


def build_real_context() -> AppContext:
    dotfiles_dir = Path(os.environ["DOTFILES_DIR"]) if "DOTFILES_DIR" in os.environ else REPO_ROOT
    return AppContext(
        runner=SubprocessRunner(),
        keychain=MacOSKeychainStore(),
        home=Path.home(),
        dotfiles_dir=dotfiles_dir,
    )
