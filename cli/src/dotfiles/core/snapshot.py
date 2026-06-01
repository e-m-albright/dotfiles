"""Machine-state snapshot: collect, persist, and diff. Pure over ProcessRunner + pathlib."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.core.models import (
    BrewState,
    SymlinkState,
)
from dotfiles.core.ports import ProcessRunner

# (runtime label -> probe command). The label is the stable key in the snapshot.
_RUNTIMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("node", ("node", "--version")),
    ("bun", ("bun", "--version")),
    ("python", ("python3", "--version")),
    ("go", ("go", "version")),
    ("rust", ("rustc", "--version")),
    ("uv", ("uv", "--version")),
)


def collect_brew(runner: ProcessRunner) -> BrewState:
    """Capture top-level brew packages: `brew leaves` + installed casks."""
    leaves = runner.run(("brew", "leaves"))
    casks = runner.run(("brew", "list", "--cask", "-1"))
    return BrewState(
        leaves=tuple(line for line in leaves.stdout.splitlines() if line.strip()),
        casks=tuple(line for line in casks.stdout.splitlines() if line.strip()),
    )


def collect_runtimes(
    runner: ProcessRunner,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, str]:
    """Capture installed runtime versions; absent tools are omitted."""
    versions: dict[str, str] = {}
    for label, cmd in _RUNTIMES:
        if which(cmd[0]) is None:
            continue
        result = runner.run(cmd)
        lines = result.stdout.strip().splitlines()
        if lines:
            versions[label] = lines[0].strip()
    return versions


# Managed symlinks the dotfiles install owns (mirrors doctor's Configuration checks).
def _managed_symlinks(*, home: Path, dotfiles_dir: Path) -> list[tuple[Path, Path]]:
    """Return (dest, src) pairs for every dotfiles-managed symlink."""
    return [
        (home / ".zshrc", dotfiles_dir / "shell" / ".zshrc"),
        (home / ".gitconfig", dotfiles_dir / "git" / ".gitconfig"),
        (home / ".zprofile", dotfiles_dir / "shell" / ".zprofile"),
    ]


def collect_symlinks(*, home: Path, dotfiles_dir: Path) -> tuple[SymlinkState, ...]:
    """Capture each managed symlink's target and whether it points where expected."""
    states: list[SymlinkState] = []
    for dest, src in _managed_symlinks(home=home, dotfiles_dir=dotfiles_dir):
        if dest.is_symlink():
            target = str(dest.readlink())
            states.append(SymlinkState(path=str(dest), target=target, ok=str(src) in target))
        else:
            states.append(SymlinkState(path=str(dest), target="", ok=False))
    return tuple(states)
