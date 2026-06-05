"""Session-management policy: retention selection, age formatting, the sweep."""

from datetime import datetime, timedelta
from pathlib import Path

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.service import (
    exited_sessions,
    humanize_age,
    maybe_prune,
    sessions_to_prune,
    should_prune,
)
from dotfiles.cmd.session.zellij import Zellij
from dotfiles.testing.fakes import FakeProcessRunner


def _zellij(runner: FakeProcessRunner) -> Zellij:
    return Zellij(runner, home=Path("/home/evan"), platform="linux")


def test_exited_sessions_keeps_only_exited_newest_first() -> None:
    sessions = [
        Session(name="live", running=True, current=False, created_age_seconds=10),
        Session(name="stale", running=False, current=False, created_age_seconds=500),
        Session(name="fresh", running=False, current=False, created_age_seconds=30),
    ]
    assert [s.name for s in exited_sessions(sessions)] == ["fresh", "stale"]


def test_exited_sessions_sorts_unknown_age_last() -> None:
    sessions = [
        Session(name="unknown", running=False, current=False, created_age_seconds=None),
        Session(name="dated", running=False, current=False, created_age_seconds=99),
    ]
    assert [s.name for s in exited_sessions(sessions)] == ["dated", "unknown"]


def test_sessions_to_prune_drops_sessions_older_than_max_age() -> None:
    exited = [
        Session(name="recent", running=False, current=False, created_age_seconds=1 * 86400),
        Session(name="ancient", running=False, current=False, created_age_seconds=20 * 86400),
        Session(name="edge", running=False, current=False, created_age_seconds=5 * 86400),
    ]
    assert sessions_to_prune(exited, max_age_days=14, max_count=100) == ["ancient"]


def test_sessions_to_prune_ignores_unknown_age_for_age_rule() -> None:
    exited = [Session(name="mystery", running=False, current=False, created_age_seconds=None)]
    assert sessions_to_prune(exited, max_age_days=14, max_count=100) == []


def test_sessions_to_prune_keeps_only_newest_max_count() -> None:
    # 25 fresh exited sessions, ages 1..25 days apart but all under max_age.
    exited = [
        Session(name=f"s{i}", running=False, current=False, created_age_seconds=i * 60)
        for i in range(25)
    ]
    pruned = sessions_to_prune(exited, max_age_days=999, max_count=20)
    # Beyond the newest 20, the 5 oldest (largest age) get dropped.
    assert set(pruned) == {f"s{i}" for i in range(20, 25)}
    assert len(pruned) == 5


def test_sessions_to_prune_unions_age_and_count_rules() -> None:
    exited = [
        Session(name="keep", running=False, current=False, created_age_seconds=60),
        Session(name="too-old", running=False, current=False, created_age_seconds=30 * 86400),
    ]
    # max_count alone keeps both; the age rule still drops the ancient one.
    assert sessions_to_prune(exited, max_age_days=14, max_count=20) == ["too-old"]


def test_humanize_age_picks_largest_unit() -> None:
    assert humanize_age(2 * 86400) == "2d"
    assert humanize_age(5400) == "1h"
    assert humanize_age(1800) == "30m"
    assert humanize_age(45) == "45s"


def test_humanize_age_handles_unknown() -> None:
    assert humanize_age(None) == "?"


def test_should_prune_true_when_never_run() -> None:
    assert should_prune(None, datetime(2026, 6, 4), timedelta(days=1))


def test_should_prune_respects_interval() -> None:
    now = datetime(2026, 6, 4, 12, 0)
    assert not should_prune(now - timedelta(hours=23), now, timedelta(days=1))
    assert should_prune(now - timedelta(hours=25), now, timedelta(days=1))


def _exited_listing() -> str:
    return (
        "mobile [Created 1h ago] (current)\n"
        "recent [Created 2h ago] (EXITED - attach to resurrect)\n"
        "old [Created 20d ago] (EXITED - attach to resurrect)\n"
    )


def test_maybe_prune_sweeps_when_due_and_stamps(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "list-sessions", "--no-formatting"), stdout=_exited_listing())
    stamp = tmp_path / "session-prune"
    now = datetime(2026, 6, 4, 12, 0)

    results = maybe_prune(_zellij(runner), state_file=stamp, now=now, max_age_days=14, max_count=20)

    # Only the >14d exited session is deleted; running + recent are untouched.
    assert ("zellij", "delete-session", "old") in runner.calls
    assert ("zellij", "delete-session", "recent") not in runner.calls
    assert [r.level for r in results] == ["success"]
    assert stamp.read_text().strip() == now.isoformat()


def test_maybe_prune_skips_when_not_due(tmp_path: Path) -> None:
    stamp = tmp_path / "session-prune"
    now = datetime(2026, 6, 4, 12, 0)
    stamp.write_text((now - timedelta(hours=1)).isoformat())
    runner = FakeProcessRunner()

    assert maybe_prune(_zellij(runner), state_file=stamp, now=now) == []
    # Not due → never even lists sessions.
    assert runner.calls == []


def test_maybe_prune_stamps_even_with_nothing_to_delete(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago] (current)\n",
    )
    stamp = tmp_path / "session-prune"
    now = datetime(2026, 6, 4, 12, 0)

    assert maybe_prune(_zellij(runner), state_file=stamp, now=now) == []
    assert stamp.read_text().strip() == now.isoformat()
    assert not any(c[:2] == ("zellij", "delete-session") for c in runner.calls)
