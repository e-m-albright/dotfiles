"""Fleet: passively discover live agent sessions and overlay the ledger.

Cursor/Pi are ledger-only in v1 (their on-disk session formats are not parsed yet);
the CLI surfaces that explicitly rather than dropping them silently.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from dotfiles.core.models import FleetSession
from dotfiles.core.ports import ProcessRunner


def decode_claude_slug(slug: str) -> str:
    """Best-effort reverse of Claude's project-dir encoding back to a cwd.

    Claude replaces path separators with '-'. A leading '-' is the root '/';
    a doubled '--' encodes a hidden-dir boundary '/.'. This is lossy (a literal
    '-' in a path component is indistinguishable from a separator) — good enough
    to label a session and to match against `git worktree list`.
    """
    placeholder = "\x00"
    s = slug.replace("--", placeholder)
    s = s.replace("-", "/")
    return s.replace(placeholder, "/.")


def _newest_mtime(files: list[Path]) -> tuple[float, Path]:
    """Return (mtime, path) of the most recently modified file."""
    return max((f.stat().st_mtime, f) for f in files)


def claude_sessions(*, home: Path, now: datetime, live_threshold: int) -> list[FleetSession]:
    """Discover live Claude sessions from ~/.claude/projects/*/*.jsonl mtimes."""
    root = home / ".claude" / "projects"
    if not root.is_dir():
        return []
    cutoff = now - timedelta(minutes=live_threshold)
    sessions: list[FleetSession] = []
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        jsonls = list(project_dir.glob("*.jsonl"))
        if not jsonls:
            continue
        mtime, newest = _newest_mtime(jsonls)
        last_active = datetime.fromtimestamp(mtime)
        if last_active < cutoff:
            continue
        sessions.append(
            FleetSession(
                vendor="claude",
                session_id=newest.stem,
                cwd=decode_claude_slug(project_dir.name),
                branch=None,
                worktree=None,
                last_active=last_active,
                task=None,
                source="transcript",
            )
        )
    return sessions


def _first_cwd(path: Path) -> str:
    """Read the first JSON line of a session file and return its 'cwd', if any."""
    try:
        with path.open() as fh:
            first = fh.readline()
        parsed: object = json.loads(first)
    except (OSError, ValueError):
        return ""
    if not isinstance(parsed, dict) or "cwd" not in parsed:
        return ""
    return str(cast(object, parsed["cwd"]))


def codex_sessions(*, home: Path, now: datetime, live_threshold: int) -> list[FleetSession]:
    """Discover live Codex sessions from ~/.codex/sessions/**/*.jsonl mtimes."""
    root = home / ".codex" / "sessions"
    if not root.is_dir():
        return []
    cutoff = now - timedelta(minutes=live_threshold)
    sessions: list[FleetSession] = []
    for path in sorted(root.rglob("*.jsonl")):
        last_active = datetime.fromtimestamp(path.stat().st_mtime)
        if last_active < cutoff:
            continue
        sessions.append(
            FleetSession(
                vendor="codex",
                session_id=path.stem,
                cwd=_first_cwd(path),
                branch=None,
                worktree=None,
                last_active=last_active,
                task=None,
                source="transcript",
            )
        )
    return sessions


def worktree_branches(runner: ProcessRunner) -> dict[str, str]:
    """Map each git worktree path to its branch via `git worktree list --porcelain`."""
    result = runner.run(("git", "worktree", "list", "--porcelain"))
    branches: dict[str, str] = {}
    current: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current = line[len("worktree ") :].strip()
        elif line.startswith("branch ") and current:
            branches[current] = line.split("refs/heads/")[-1].strip()
        elif not line.strip():
            current = None
    return branches
