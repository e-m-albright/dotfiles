"""Transcript-mtime discovery for the TUI Sessions pane (clock injected)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotfiles.cmd.session.agent_sessions import decode_claude_slug, live_agents


def test_decode_claude_slug() -> None:
    assert decode_claude_slug("-Users-evan-myapp") == "/Users/evan/myapp"
    assert decode_claude_slug("-Users-evan--config-nvim") == "/Users/evan/.config/nvim"


def _touch(path: Path, when: datetime, body: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def test_live_agents_discovers_recent_claude_and_codex(tmp_path: Path) -> None:
    now = datetime(2026, 6, 1, 12, 0, 0)
    _touch(tmp_path / ".claude/projects/-Users-evan-app/s.jsonl", datetime(2026, 6, 1, 11, 58))
    _touch(tmp_path / ".claude/projects/-Users-evan-old/s.jsonl", datetime(2026, 6, 1, 10, 0))
    _touch(
        tmp_path / ".codex/sessions/2026/06/s.jsonl",
        datetime(2026, 6, 1, 11, 59),
        body='{"cwd": "/Users/evan/svc"}\n',
    )

    agents = live_agents(home=tmp_path, now=now, window_minutes=15)
    found = {(a.agent, a.cwd) for a in agents}

    assert ("claude", "/Users/evan/app") in found
    assert ("codex", "/Users/evan/svc") in found
    assert all(a.cwd != "/Users/evan/old" for a in agents)  # stale excluded by window
    assert agents == sorted(agents, key=lambda a: a.last_active, reverse=True)  # newest first


def test_live_agents_empty_when_no_transcript_dirs(tmp_path: Path) -> None:
    assert live_agents(home=tmp_path, now=datetime(2026, 6, 1), window_minutes=15) == []
