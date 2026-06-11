"""Machine-state snapshot: collect, persist, and diff. Pure over ProcessRunner + pathlib."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.agent import OVERVIEW_AGENTS, Agent
from dotfiles.cmd.agent.models import AgentOverview
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.cmd.snapshot.models import (
    BrewState,
    RuntimeChange,
    Snapshot,
    SnapshotDiff,
    SymlinkChange,
    SymlinkState,
)

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


def _vendor_tokens(overview: AgentOverview, agent: Agent) -> list[str]:
    """Stable, sorted tokens describing one agent's deployed agentic config."""
    tokens: list[str] = []
    for row in overview.mcp:
        if row.cells.get(agent, False):
            tokens.append(f"mcp:{row.label}")
    for hook in overview.hooks:
        if hook.cells.get(agent, False):
            tokens.append(f"hook:{hook.label}")
    if agent == "claude":
        tokens.append(f"skills:{overview.skills.deployed.get('claude', 0)}")
        tokens.append(f"rules:{overview.rules.claude_deployed}")
    elif agent == "cursor":
        tokens.append(f"rules:{overview.rules.cursor_deployed}")
    elif agent == "codex":
        tokens.append(f"skills:{overview.skills.deployed.get('codex', 0)}")
    return sorted(tokens)


def agent_config_hashes(overview: AgentOverview) -> dict[str, str]:
    """A stable content hash of each agent's deployed MCP/hooks/skills/rules."""
    hashes: dict[str, str] = {}
    for agent in OVERVIEW_AGENTS:
        joined = "\n".join(_vendor_tokens(overview, agent))
        hashes[agent] = hashlib.sha256(joined.encode()).hexdigest()[:12]
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


def _runtime_changes(old: Snapshot, new: Snapshot) -> tuple[RuntimeChange, ...]:
    changes: list[RuntimeChange] = []
    for name in sorted(set(old.runtimes) | set(new.runtimes)):
        before = old.runtimes.get(name, "")
        after = new.runtimes.get(name, "")
        if before != after:
            changes.append(RuntimeChange(name=name, old=before, new=after))
    return tuple(changes)


def _symlink_changes(old: Snapshot, new: Snapshot) -> tuple[SymlinkChange, ...]:
    old_by_path = {s.path: s for s in old.symlinks}
    changes: list[SymlinkChange] = []
    for s in new.symlinks:
        prev = old_by_path.get(s.path)
        if prev is None or prev.target != s.target or prev.ok != s.ok:
            changes.append(
                SymlinkChange(
                    path=s.path,
                    old_target=prev.target if prev else "",
                    new_target=s.target,
                    broke=(not s.ok) and (prev is None or prev.ok),
                )
            )
    return tuple(changes)


def diff(old: Snapshot, new: Snapshot) -> SnapshotDiff:
    """Compute the drift from `old` to `new` across all snapshot categories."""
    old_brew = set(old.brew.leaves) | set(old.brew.casks)
    new_brew = set(new.brew.leaves) | set(new.brew.casks)
    config_changed = tuple(
        sorted(
            v
            for v in set(old.agent_config) | set(new.agent_config)
            if old.agent_config.get(v) != new.agent_config.get(v)
        )
    )
    return SnapshotDiff(
        brew_added=tuple(sorted(new_brew - old_brew)),
        brew_removed=tuple(sorted(old_brew - new_brew)),
        runtimes_changed=_runtime_changes(old, new),
        symlinks_changed=_symlink_changes(old, new),
        agent_config_changed=config_changed,
    )
