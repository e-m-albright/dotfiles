from pathlib import Path

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.service import (
    attach_command,
    attached_client_count,
    delete_session,
    group_sessions,
    kill_session,
    layout_name_for,
    list_sessions,
    parse_sessions,
    valid_session_name,
)
from dotfiles.testing.fakes import FakeProcessRunner


def test_delete_session_runs_delete_and_reports() -> None:
    runner = FakeProcessRunner()
    step = delete_session(runner, "old")
    assert ("zellij", "delete-session", "old") in runner.calls
    assert step.level == "success"


def test_delete_session_reports_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "delete-session", "old"), exit_code=1, stderr="nope")
    assert delete_session(runner, "old").level == "error"


def test_valid_session_name_rejects_empty_and_whitespace() -> None:
    assert valid_session_name("api")
    assert valid_session_name("api-server_2")
    assert not valid_session_name("")
    assert not valid_session_name("two words")
    assert not valid_session_name("  ")


def test_group_sessions_splits_active_and_resurrectable() -> None:
    sessions = [
        Session(name="mobile", running=True, current=False),
        Session(name="old", running=False, current=False),
        Session(name="work", running=True, current=True),
        Session(name="archived", running=False, current=False),
    ]
    sections = group_sessions(sessions)
    assert [title for title, _ in sections] == ["ACTIVE", "RESURRECTABLE"]
    # Current first within ACTIVE, then by name; exited sorted by name.
    assert [s.name for s in sections[0][1]] == ["work", "mobile"]
    assert [s.name for s in sections[1][1]] == ["archived", "old"]


def test_group_sessions_omits_empty_groups() -> None:
    only_active = [Session(name="work", running=True, current=True)]
    assert [t for t, _ in group_sessions(only_active)] == ["ACTIVE"]
    only_dead = [Session(name="old", running=False, current=False)]
    assert [t for t, _ in group_sessions(only_dead)] == ["RESURRECTABLE"]
    assert group_sessions([]) == []


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
