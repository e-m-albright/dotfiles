"""Append-only agent-activity ledger. Pure over pathlib; core owns the schema."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from dotfiles.core.logging import get_logger
from dotfiles.core.models import LedgerEntry

_LEDGER = "ledger.jsonl"
_log = get_logger(__name__)


def append(state_dir: Path, entry: LedgerEntry) -> None:
    """Append one entry as a JSON line. Tolerant — never raises into a caller's hot path."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / _LEDGER).open("a") as fh:
            fh.write(entry.model_dump_json() + "\n")
    except OSError as exc:
        # Hot-path hook must never fail because of the ledger — degrade, but trace it.
        _log.debug("ledger_append_failed", state_dir=str(state_dir), error=str(exc))


def read(state_dir: Path) -> list[LedgerEntry]:
    """Parse the ledger, skipping malformed lines (forward-compatible)."""
    path = state_dir / _LEDGER
    if not path.exists():
        return []
    entries: list[LedgerEntry] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entries.append(LedgerEntry.model_validate_json(line))
        except ValueError as exc:
            _log.debug("ledger_skip_bad_line", path=str(path), error=str(exc))
            continue
    return entries


def latest_by_session(entries: list[LedgerEntry]) -> dict[str, LedgerEntry]:
    """Collapse to the most-recent entry per session_id (the fleet join key)."""
    latest: dict[str, LedgerEntry] = {}
    for entry in entries:
        current = latest.get(entry.session_id)
        if current is None or entry.ts >= current.ts:
            latest[entry.session_id] = entry
    return latest


def prune(state_dir: Path, *, older_than: datetime) -> int:
    """Drop entries older than `older_than`; rewrite the file. Returns count removed."""
    entries = read(state_dir)
    kept = [e for e in entries if e.ts >= older_than]
    removed = len(entries) - len(kept)
    if removed:
        path = state_dir / _LEDGER
        path.write_text("".join(e.model_dump_json() + "\n" for e in kept))
    return removed
