from dotfiles.core.models import Session
from dotfiles.core.sessions import attach_command, kill_session, list_sessions, parse_sessions
from tests.fakes import FakeProcessRunner


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
        Session(name="mobile", running=True, current=False),
        Session(name="work", running=True, current=True),
        Session(name="old", running=False, current=False),
    ]


def test_attach_command_uses_create() -> None:
    assert attach_command("mobile") == ("zellij", "attach", "--create", "mobile")


def test_service_list_parses_runner_output() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago]\nwork [Created 5m ago] (current)\n",
    )
    names = [s.name for s in list_sessions(runner)]
    assert names == ["mobile", "work"]


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

    from dotfiles.core.sessions import SessionError

    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="",
        stderr="zellij: command broke",
    )
    with pytest.raises(SessionError, match="command broke"):
        list_sessions(runner)
