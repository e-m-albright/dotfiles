"""Transcript-mtime discovery for the TUI Sessions pane (clock injected)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotfiles.cmd.session.agent_sessions import (
    decode_claude_slug,
    live_agents,
    match_agents_to_sessions,
)
from dotfiles.cmd.session.models import AgentActivity


def _agent(cwd: str) -> AgentActivity:
    return AgentActivity(agent="claude", cwd=cwd, last_active=datetime(2026, 6, 1, 12, 0))


def test_match_agents_exact_cwd() -> None:
    matched, unmatched = match_agents_to_sessions(
        {"dotfiles": "/Users/evan/dotfiles"}, [_agent("/Users/evan/dotfiles")]
    )
    assert [a.cwd for a in matched["dotfiles"]] == ["/Users/evan/dotfiles"]
    assert unmatched == []


def test_match_agents_nested_cwd_picks_deepest_session() -> None:
    # An agent in dotfiles/cli matches both the home session and dotfiles; the
    # deepest (most specific) cwd wins.
    matched, unmatched = match_agents_to_sessions(
        {"home": "/Users/evan", "dotfiles": "/Users/evan/dotfiles"},
        [_agent("/Users/evan/dotfiles/cli")],
    )
    assert "dotfiles" in matched
    assert "home" not in matched
    assert unmatched == []


def test_match_agents_unmatched_when_no_session_contains_cwd() -> None:
    matched, unmatched = match_agents_to_sessions(
        {"dotfiles": "/Users/evan/dotfiles"}, [_agent("/Users/evan/code/public")]
    )
    assert matched == {}
    assert [a.cwd for a in unmatched] == ["/Users/evan/code/public"]


def test_match_agents_sibling_prefix_is_not_a_match() -> None:
    # /Users/evan/dotfiles-old must not match the /Users/evan/dotfiles session.
    _, unmatched = match_agents_to_sessions(
        {"dotfiles": "/Users/evan/dotfiles"}, [_agent("/Users/evan/dotfiles-old")]
    )
    assert [a.cwd for a in unmatched] == ["/Users/evan/dotfiles-old"]


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
