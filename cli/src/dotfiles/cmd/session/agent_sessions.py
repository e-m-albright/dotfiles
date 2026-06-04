"""Discover recently-active agent sessions from transcript file mtimes.

Read-only and cooperation-free: scans Claude and Codex transcript directories and
reports which agents have been active inside a time window. The TUI Sessions pane
uses this so the phone deck shows your live agent work next to the zellij sessions.
`now` is injected — the core never reads the clock.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from dotfiles.cmd.session.models import AgentActivity


def decode_claude_slug(slug: str) -> str:
    """Best-effort reverse of Claude's project-dir encoding back to a cwd.

    Claude replaces path separators with ``-`` and a hidden-dir boundary ``/.``
    with ``--``. Lossy (a literal ``-`` in a component is indistinguishable from a
    separator) but good enough to label a session.
    """
    placeholder = "\x00"
    s = slug.replace("--", placeholder).replace("-", "/")
    return s.replace(placeholder, "/.")


def _first_cwd(path: Path) -> str:
    """Return the ``cwd`` from a session file's first JSON line, or ``""``."""
    try:
        with path.open() as fh:
            parsed: object = json.loads(fh.readline())
    except (OSError, ValueError):
        return ""
    if isinstance(parsed, dict) and "cwd" in parsed:
        return str(cast(object, parsed["cwd"]))
    return ""


def _claude(home: Path, cutoff: datetime) -> list[AgentActivity]:
    root = home / ".claude" / "projects"
    if not root.is_dir():
        return []
    out: list[AgentActivity] = []
    for project_dir in (p for p in root.iterdir() if p.is_dir()):
        jsonls = list(project_dir.glob("*.jsonl"))
        if not jsonls:
            continue
        last_active = datetime.fromtimestamp(max(f.stat().st_mtime for f in jsonls))
        if last_active >= cutoff:
            out.append(
                AgentActivity(
                    agent="claude",
                    cwd=decode_claude_slug(project_dir.name),
                    last_active=last_active,
                )
            )
    return out


def _codex(home: Path, cutoff: datetime) -> list[AgentActivity]:
    root = home / ".codex" / "sessions"
    if not root.is_dir():
        return []
    out: list[AgentActivity] = []
    for path in root.rglob("*.jsonl"):
        last_active = datetime.fromtimestamp(path.stat().st_mtime)
        if last_active >= cutoff:
            out.append(AgentActivity(agent="codex", cwd=_first_cwd(path), last_active=last_active))
    return out


def live_agents(*, home: Path, now: datetime, window_minutes: int = 15) -> list[AgentActivity]:
    """Claude + Codex sessions active within *window_minutes*, newest first."""
    cutoff = now - timedelta(minutes=window_minutes)
    found = _claude(home, cutoff) + _codex(home, cutoff)
    return sorted(found, key=lambda a: a.last_active, reverse=True)


def _deepest_session_for(cwd: str, session_cwds: dict[str, str]) -> str | None:
    """Session name whose cwd most specifically contains *cwd*, or None."""
    candidates = [
        (name, base.rstrip("/"))
        for name, base in session_cwds.items()
        if cwd == base.rstrip("/") or cwd.startswith(base.rstrip("/") + "/")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda nb: len(nb[1]))[0]


def match_agents_to_sessions(
    session_cwds: dict[str, str], agents: list[AgentActivity]
) -> tuple[dict[str, list[AgentActivity]], list[AgentActivity]]:
    """Group agents under the session whose cwd contains them; deepest cwd wins.

    An agent matches a session when its cwd equals the session's cwd or is nested
    beneath it. Agents matching no session land in the returned "unmatched" list.
    """
    matched: dict[str, list[AgentActivity]] = {}
    unmatched: list[AgentActivity] = []
    for agent in agents:
        best = _deepest_session_for(agent.cwd, session_cwds)
        if best is None:
            unmatched.append(agent)
        else:
            matched.setdefault(best, []).append(agent)
    return matched, unmatched
