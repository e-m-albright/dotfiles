"""Ledger core: append-only JSONL of agent activity."""

from datetime import datetime

from dotfiles.core.ledger import append, latest_by_session, prune, read
from dotfiles.core.models import LedgerEntry


def _entry(**kw) -> LedgerEntry:
    base: dict = {
        "ts": datetime(2026, 6, 1, 12, 0, 0),
        "session_id": "s1",
        "vendor": "claude",
        "cwd": "/home/e/dotfiles",
        "branch": "main",
        "task": "build fleet",
        "status": "active",
    }
    base.update(kw)
    return LedgerEntry(**base)


def test_append_then_read_round_trips(tmp_path):
    append(tmp_path, _entry())
    append(tmp_path, _entry(session_id="s2", task="other"))
    entries = read(tmp_path)
    assert [e.session_id for e in entries] == ["s1", "s2"]
    assert entries[0].task == "build fleet"


def test_read_missing_file_is_empty(tmp_path):
    assert read(tmp_path) == []


def test_read_skips_malformed_lines(tmp_path):
    (tmp_path).mkdir(exist_ok=True)
    (tmp_path / "ledger.jsonl").write_text('{"not":"valid"}\n' + _entry().model_dump_json() + "\n")
    entries = read(tmp_path)
    assert len(entries) == 1
    assert entries[0].session_id == "s1"


def test_latest_by_session_keeps_newest(tmp_path):
    append(tmp_path, _entry(ts=datetime(2026, 6, 1, 10, 0), task="old"))
    append(tmp_path, _entry(ts=datetime(2026, 6, 1, 11, 0), task="new"))
    latest = latest_by_session(read(tmp_path))
    assert latest["s1"].task == "new"


def test_prune_drops_old_entries(tmp_path):
    append(tmp_path, _entry(ts=datetime(2026, 6, 1, 8, 0), session_id="old"))
    append(tmp_path, _entry(ts=datetime(2026, 6, 1, 20, 0), session_id="keep"))
    removed = prune(tmp_path, older_than=datetime(2026, 6, 1, 12, 0))
    assert removed == 1
    assert [e.session_id for e in read(tmp_path)] == ["keep"]
