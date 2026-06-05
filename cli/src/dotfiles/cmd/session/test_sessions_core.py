from datetime import datetime, timedelta
from pathlib import Path

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.service import (
    attach_command,
    attached_client_count,
    delete_session,
    exited_sessions,
    humanize_age,
    kill_session,
    layout_name_for,
    list_sessions,
    maybe_prune,
    parse_sessions,
    prune_exited,
    sessions_to_prune,
    should_prune,
)
from dotfiles.testing.fakes import FakeProcessRunner


def test_parse_empty() -> None:
    assert parse_sessions("No active zellij sessions found.\n") == []
    assert parse_sessions("") == []


def test_parse_running_current_and_exited() -> None:
    out = (
        "mobile [Created 1h 30m ago]\n"
        "work [Created 5m ago] (current)\n"
        "old [Created 2d ago] (EXITED - attach to resurrect)\n"
    )
    sessions = parse_sessions(out)
    assert sessions == [
        Session(name="mobile", running=True, current=False, created_age_seconds=90 * 60),
        Session(name="work", running=True, current=True, created_age_seconds=5 * 60),
        Session(name="old", running=False, current=False, created_age_seconds=2 * 86400),
    ]


def test_parse_captures_created_age_seconds() -> None:
    out = (
        "mobile [Created 1h 30m ago]\n"
        "old [Created 2d ago] (EXITED - attach to resurrect)\n"
        "precise [Created 10h 40m 27s ago]\n"
    )
    by_name = {s.name: s.created_age_seconds for s in parse_sessions(out)}
    assert by_name["mobile"] == 90 * 60
    assert by_name["old"] == 2 * 86400
    assert by_name["precise"] == 10 * 3600 + 40 * 60 + 27


def test_parse_created_age_is_none_when_absent() -> None:
    # A line zellij prints without a "[Created ... ago]" clause.
    assert parse_sessions("weird-session\n")[0].created_age_seconds is None


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


def test_attach_command_uses_create() -> None:
    assert attach_command("mobile") == ("zellij", "attach", "--create", "mobile")


def test_attach_command_with_layout_creates_when_absent() -> None:
    assert attach_command("mobile", exists=False, layout="mobile") == (
        "zellij",
        "--session",
        "mobile",
        "--layout",
        "mobile",
    )


def test_attach_command_with_layout_plain_attaches_when_present() -> None:
    # A layout can only apply on creation, so an existing session just attaches.
    assert attach_command("mobile", exists=True, layout="mobile") == (
        "zellij",
        "attach",
        "mobile",
    )


def test_attach_command_without_layout_ignores_exists() -> None:
    assert attach_command("work", exists=True, layout=None) == (
        "zellij",
        "attach",
        "--create",
        "work",
    )


def test_layout_name_for_finds_deployed_layout(tmp_path: Path) -> None:
    layouts = tmp_path / ".config" / "zellij" / "layouts"
    layouts.mkdir(parents=True)
    (layouts / "mobile.kdl").write_text("layout {}\n")
    assert layout_name_for(tmp_path, "mobile") == "mobile"
    assert layout_name_for(tmp_path, "work") is None


def test_attached_client_count_none_outside_session() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "action", "list-clients"), exit_code=1, stderr="no active session")
    assert attached_client_count(runner) is None


def test_attached_client_count_counts_id_rows() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "action", "list-clients"),
        stdout="CLIENT_ID PANE_ID RUNNING_COMMAND\n1 terminal_2 zsh\n2 terminal_5 dotfiles tui\n",
    )
    assert attached_client_count(runner) == 2


def test_service_list_parses_runner_output() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago]\nwork [Created 5m ago] (current)\n",
    )
    names = [s.name for s in list_sessions(runner)]
    assert names == ["mobile", "work"]


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

    results = maybe_prune(runner, state_file=stamp, now=now, max_age_days=14, max_count=20)

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

    assert maybe_prune(runner, state_file=stamp, now=now) == []
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

    assert maybe_prune(runner, state_file=stamp, now=now) == []
    assert stamp.read_text().strip() == now.isoformat()
    assert not any(c[:2] == ("zellij", "delete-session") for c in runner.calls)


def test_prune_exited_deletes_each_named_session() -> None:
    runner = FakeProcessRunner()
    results = prune_exited(runner, ["old", "stale"])
    assert ("zellij", "delete-session", "old") in runner.calls
    assert ("zellij", "delete-session", "stale") in runner.calls
    assert [r.level for r in results] == ["success", "success"]


def test_prune_exited_empty_is_a_noop() -> None:
    runner = FakeProcessRunner()
    assert prune_exited(runner, []) == []
    assert runner.calls == []


def test_service_delete_runs_delete_session_and_reports() -> None:
    runner = FakeProcessRunner()
    step = delete_session(runner, "old")
    assert ("zellij", "delete-session", "old") in runner.calls
    assert step.level == "success"


def test_service_delete_reports_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "delete-session", "old"), exit_code=1, stderr="no such session")
    step = delete_session(runner, "old")
    assert step.level == "error"


def test_service_kill_runs_kill_session_and_reports() -> None:
    runner = FakeProcessRunner()
    step = kill_session(runner, "work")
    assert ("zellij", "kill-session", "work") in runner.calls
    assert step.level == "success"


def test_service_kill_reports_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "kill-session", "work"), exit_code=1, stderr="no session")
    step = kill_session(runner, "work")
    assert step.level == "error"


def test_list_returns_empty_even_if_zellij_exits_nonzero_on_no_sessions() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="No active zellij sessions found.\n",
    )
    assert list_sessions(runner) == []


def test_list_returns_empty_when_marker_is_in_stderr() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="",
        stderr="No active zellij sessions found.\n",
    )
    assert list_sessions(runner) == []


def test_list_raises_on_real_failure() -> None:
    import pytest

    from dotfiles.cmd.session.service import SessionError

    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="",
        stderr="zellij: command broke",
    )
    with pytest.raises(SessionError, match="command broke"):
        list_sessions(runner)
