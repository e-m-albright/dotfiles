"""Machine-state snapshot: collect, persist, and diff. Pure over ProcessRunner + pathlib."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from dotfiles.core.agent_overview import AgentOverviewService
from dotfiles.core.models import (
    AgentOverview,
    BrewState,
    Snapshot,
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


def _vendor_tokens(overview: AgentOverview, vendor: str) -> list[str]:
    """Stable, sorted tokens describing one vendor's deployed agentic config."""
    tokens: list[str] = []
    for row in overview.mcp:
        if getattr(row, vendor, False):
            tokens.append(f"mcp:{row.server}")
    for hook in overview.hooks:
        if getattr(hook, vendor, False):
            tokens.append(f"hook:{hook.event}")
    if vendor == "claude":
        tokens.append(f"skills:{overview.skills.claude_deployed}")
        tokens.append(f"rules:{overview.rules.claude_deployed}")
    elif vendor == "cursor":
        tokens.append(f"rules:{overview.rules.cursor_deployed}")
    elif vendor == "codex":
        tokens.append(f"skills:{overview.skills.shared_deployed}")
    return sorted(tokens)


def agent_config_hashes(overview: AgentOverview) -> dict[str, str]:
    """A stable content hash of each vendor's deployed MCP/hooks/skills/rules."""
    hashes: dict[str, str] = {}
    for vendor in ("claude", "cursor", "codex", "gemini"):
        joined = "\n".join(_vendor_tokens(overview, vendor))
        hashes[vendor] = hashlib.sha256(joined.encode()).hexdigest()[:12]
    return hashes


def capture(
    runner: ProcessRunner,
    *,
    dotfiles_dir: Path,
    home: Path,
    taken_at: datetime,
    which: Callable[[str], str | None] = shutil.which,
) -> Snapshot:
    """Collect a full machine-state snapshot. `taken_at` is injected (never now() in core)."""
    overview = AgentOverviewService(
        runner=runner, dotfiles_dir=dotfiles_dir, home=home, which=which
    ).overview()
    return Snapshot(
        taken_at=taken_at,
        brew=collect_brew(runner),
        runtimes=collect_runtimes(runner, which=which),
        symlinks=collect_symlinks(home=home, dotfiles_dir=dotfiles_dir),
        agent_config=agent_config_hashes(overview),
    )


def _slug(taken_at: datetime) -> str:
    """Filesystem-safe timestamp slug, e.g. 2026-06-01T09-00-00."""
    return taken_at.strftime("%Y-%m-%dT%H-%M-%S")


def write_snapshot(state_dir: Path, snapshot: Snapshot) -> Path:
    """Persist a snapshot as JSON under state_dir/snapshots/. Returns the file path."""
    snap_dir = state_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / f"{_slug(snapshot.taken_at)}.json"
    path.write_text(snapshot.model_dump_json(indent=2))
    return path


def list_snapshots(state_dir: Path) -> list[Path]:
    """All saved snapshot files, newest first (lexical sort works on the ISO slug)."""
    snap_dir = state_dir / "snapshots"
    if not snap_dir.is_dir():
        return []
    return sorted(snap_dir.glob("*.json"), reverse=True)


def load_snapshot(path: Path) -> Snapshot:
    """Load a snapshot from its JSON file."""
    return Snapshot.model_validate_json(path.read_text())
