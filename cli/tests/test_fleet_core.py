"""Fleet core: passive discovery + ledger overlay."""

import os
from datetime import datetime

from dotfiles.core.fleet import claude_sessions, decode_claude_slug


def _touch(path, when: datetime):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def test_decode_claude_slug_simple():
    assert decode_claude_slug("-Users-evan-code-evan") == "/Users/evan/code/evan"


def test_decode_claude_slug_hidden_dir():
    # "--" encodes "/." (a hidden directory boundary)
    assert (
        decode_claude_slug("-Users-evan--claude-worktrees-x") == "/Users/evan/.claude/worktrees/x"
    )


def test_claude_sessions_discovers_live_only(tmp_path):
    home = tmp_path / "home"
    now = datetime(2026, 6, 1, 12, 0, 0)
    _touch(home / ".claude/projects/-Users-evan-code-evan/abc.jsonl", datetime(2026, 6, 1, 11, 55))
    _touch(home / ".claude/projects/-Users-evan-old/stale.jsonl", datetime(2026, 6, 1, 9, 0))
    sessions = claude_sessions(home=home, now=now, live_threshold=15)
    assert [s.cwd for s in sessions] == ["/Users/evan/code/evan"]
    assert sessions[0].vendor == "claude"
    assert sessions[0].session_id == "abc"
    assert sessions[0].source == "transcript"
