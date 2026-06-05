"""The zellij seam: list-output/cache format (pure) and the Zellij facade (I/O)."""

from pathlib import Path

import pytest

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.zellij import (
    SessionError,
    Zellij,
    attach_command,
    handoff_command,
    layout_name_for,
    parse_pane_titles,
    parse_sessions,
    zellij_cache_root,
)
from dotfiles.testing.fakes import FakeProcessRunner


def _zellij(runner: FakeProcessRunner, *, home: Path = Path("/home/evan")) -> Zellij:
    return Zellij(runner, home=home, platform="linux")


# --- list-output format (pure) ----------------------------------------------


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


# --- command/path builders (pure) -------------------------------------------


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
    assert attach_command("mobile", exists=True, layout="mobile") == ("zellij", "attach", "mobile")


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


def test_handoff_attaches_when_not_in_zellij() -> None:
    assert handoff_command("mobile", in_zellij=False) == ("zellij", "attach", "--create", "mobile")


def test_handoff_switches_when_in_zellij() -> None:
    assert handoff_command("mobile", in_zellij=True) == (
        "zellij",
        "action",
        "switch-session",
        "mobile",
    )


# --- cache format (pure) -----------------------------------------------------


# Trimmed from a real session-metadata.kdl: one terminal pane + two plugin panes
# (chrome) + one suppressed plugin overlay. Only the terminal pane should surface.
_METADATA = """\
name "banana"
tabs {
    tab {
        position 0
        name "Tab #1"
    }
}
panes {
    pane {
        id 0
        is_plugin false
        title "✳ Claude Code"
        exited false
        is_suppressed false
    }
    pane {
        id 1
        is_plugin true
        title "tab-bar"
        plugin_url "tab-bar"
    }
    pane {
        id 2
        is_plugin true
        title "status-bar"
        plugin_url "status-bar"
    }
    pane {
        id 0
        is_plugin true
        is_suppressed true
        title "(.) - zellij:link"
        plugin_url "zellij:link"
    }
}
connected_clients 1
"""


def test_parse_pane_titles_keeps_only_real_terminal_panes() -> None:
    assert parse_pane_titles(_METADATA) == ["✳ Claude Code"]


def test_parse_pane_titles_skips_exited_panes() -> None:
    metadata = """\
panes {
    pane { id 0 is_plugin false exited true title "old vim" }
    pane { id 1 is_plugin false exited false title "zsh" }
}
"""
    assert parse_pane_titles(metadata) == ["zsh"]


def test_parse_pane_titles_empty_when_no_panes_section() -> None:
    assert parse_pane_titles('name "x"\n') == []


def test_zellij_cache_root_is_os_specific(monkeypatch) -> None:
    home = Path("/home/evan")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert zellij_cache_root(home, "linux") == home / ".cache" / "zellij"
    assert (
        zellij_cache_root(home, "darwin")
        == home / "Library" / "Caches" / "org.Zellij-Contributors.Zellij"
    )
    monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")
    assert zellij_cache_root(home, "linux") == Path("/custom/cache") / "zellij"


# --- the Zellij facade (I/O over the ProcessRunner port + the cache) ---------


def test_list_sessions_parses_runner_output() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago]\nwork [Created 5m ago] (current)\n",
    )
    assert [s.name for s in _zellij(runner).list_sessions()] == ["mobile", "work"]


def test_list_sessions_empty_even_if_zellij_exits_nonzero_on_no_sessions() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="No active zellij sessions found.\n",
    )
    assert _zellij(runner).list_sessions() == []


def test_list_sessions_empty_when_marker_is_in_stderr() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="",
        stderr="No active zellij sessions found.\n",
    )
    assert _zellij(runner).list_sessions() == []


def test_list_sessions_raises_on_real_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        exit_code=1,
        stdout="",
        stderr="zellij: command broke",
    )
    with pytest.raises(SessionError, match="command broke"):
        _zellij(runner).list_sessions()


def test_attached_client_count_none_outside_session() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "action", "list-clients"), exit_code=1, stderr="no active session")
    assert _zellij(runner).attached_client_count() is None


def test_attached_client_count_counts_id_rows() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "action", "list-clients"),
        stdout="CLIENT_ID PANE_ID RUNNING_COMMAND\n1 terminal_2 zsh\n2 terminal_5 dotfiles tui\n",
    )
    assert _zellij(runner).attached_client_count() == 2


def test_kill_session_runs_command_and_reports() -> None:
    runner = FakeProcessRunner()
    step = _zellij(runner).kill_session("work")
    assert ("zellij", "kill-session", "work") in runner.calls
    assert step.level == "success"


def test_kill_session_reports_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "kill-session", "work"), exit_code=1, stderr="no session")
    assert _zellij(runner).kill_session("work").level == "error"


def test_delete_session_runs_command_and_reports() -> None:
    runner = FakeProcessRunner()
    step = _zellij(runner).delete_session("old")
    assert ("zellij", "delete-session", "old") in runner.calls
    assert step.level == "success"


def test_delete_session_reports_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "delete-session", "old"), exit_code=1, stderr="no such session")
    assert _zellij(runner).delete_session("old").level == "error"


def test_prune_deletes_each_named_session() -> None:
    runner = FakeProcessRunner()
    results = _zellij(runner).prune(["old", "stale"])
    assert ("zellij", "delete-session", "old") in runner.calls
    assert ("zellij", "delete-session", "stale") in runner.calls
    assert [r.level for r in results] == ["success", "success"]


def test_prune_empty_is_a_noop() -> None:
    runner = FakeProcessRunner()
    assert _zellij(runner).prune([]) == []
    assert runner.calls == []


def test_program_titles_reads_from_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    info = tmp_path / "zellij" / "contract_version_1" / "session_info" / "banana"
    info.mkdir(parents=True)
    (info / "session-metadata.kdl").write_text(_METADATA)
    assert _zellij(FakeProcessRunner(), home=tmp_path).program_titles("banana") == ["✳ Claude Code"]


def test_program_titles_degrades_to_empty_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert _zellij(FakeProcessRunner(), home=tmp_path).program_titles("ghost") == []
