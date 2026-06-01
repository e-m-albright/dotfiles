"""Ledger core: append-only JSONL of agent activity."""

from datetime import datetime

from dotfiles.core.ledger import append, read
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
