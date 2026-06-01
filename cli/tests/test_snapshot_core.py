"""Snapshot models + core logic."""

from datetime import datetime

from dotfiles.core.models import BrewState, Snapshot, SymlinkState


def test_snapshot_round_trips_through_json():
    snap = Snapshot(
        taken_at=datetime(2026, 6, 1, 14, 2, 9),
        brew=BrewState(leaves=("git", "jq"), casks=("cursor",)),
        runtimes={"node": "v22.3.0", "uv": "uv 0.5.0"},
        symlinks=(SymlinkState(path="/home/e/.zshrc", target="/d/shell/.zshrc", ok=True),),
        agent_config={"claude": "abc123"},
    )
    restored = Snapshot.model_validate_json(snap.model_dump_json())
    assert restored == snap
