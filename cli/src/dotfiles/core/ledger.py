"""Append-only agent-activity ledger. Pure over pathlib; core owns the schema."""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.models import LedgerEntry

_LEDGER = "ledger.jsonl"


def append(state_dir: Path, entry: LedgerEntry) -> None:
    """Append one entry as a JSON line. Tolerant — never raises into a caller's hot path."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / _LEDGER).open("a") as fh:
            fh.write(entry.model_dump_json() + "\n")
    except OSError:
        pass


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
        except ValueError:
            continue
    return entries
