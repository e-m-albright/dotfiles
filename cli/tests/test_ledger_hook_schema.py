"""The hot-path shell hook must write exactly the LedgerEntry fields."""

from pathlib import Path

from dotfiles.core.models import LedgerEntry

# repo root: cli/tests/ -> parents[2]
_HOOK = Path(__file__).resolve().parents[2] / "agents" / "shared" / "ledger-hook.sh"


def test_hook_writes_every_ledger_field():
    text = _HOOK.read_text()
    for field in LedgerEntry.model_fields:
        assert f'"{field}"' in text, f"ledger-hook.sh is missing JSON key {field!r}"
