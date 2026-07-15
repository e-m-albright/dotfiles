"""Session-management policy: retention selection and age formatting."""

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.service import (
    exited_sessions,
    humanize_age,
    sessions_to_prune,
)


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
