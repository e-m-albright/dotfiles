"""Fleet core: passive discovery + ledger overlay."""

import json
import os
from datetime import datetime

from dotfiles.core.fleet import (
    claude_sessions,
    codex_sessions,
    decode_claude_slug,
    worktree_branches,
)
from tests.fakes import FakeProcessRunner


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


def test_codex_sessions_parse_cwd_from_first_line(tmp_path):
    home = tmp_path / "home"
    now = datetime(2026, 6, 1, 12, 0, 0)
    p = home / ".codex/sessions/2026/06/sess1.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"cwd": "/home/evan/site"}) + "\n")
    ts = datetime(2026, 6, 1, 11, 58).timestamp()
    os.utime(p, (ts, ts))
    sessions = codex_sessions(home=home, now=now, live_threshold=15)
    assert sessions[0].vendor == "codex"
    assert sessions[0].cwd == "/home/evan/site"
    assert sessions[0].session_id == "sess1"


def test_worktree_branches_parses_porcelain():
    runner = FakeProcessRunner()
    runner.script(
        ("git", "worktree", "list", "--porcelain"),
        stdout=(
            "worktree /home/evan/dotfiles\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /home/evan/.worktrees/feat\n"
            "branch refs/heads/feat/x\n"
        ),
    )
    branches = worktree_branches(runner)
    assert branches == {
        "/home/evan/dotfiles": "main",
        "/home/evan/.worktrees/feat": "feat/x",
    }
