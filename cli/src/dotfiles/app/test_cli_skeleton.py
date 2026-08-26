from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from dotfiles.app import main
from dotfiles.app.main import app
from dotfiles.testing.fakes import make_fake_context

runner = CliRunner()


def test_help_lists_top_level_command_tree() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("remote", "session", "doctor", "brew", "tui", "email-mask"):
        assert command in result.output


def test_session_alias_sesh_is_removed() -> None:
    # `sesh` was retired in favour of the full `session` spelling.
    result = runner.invoke(app, ["sesh", "--help"])
    assert result.exit_code != 0


def test_root_callback_builds_context_when_none_injected() -> None:
    # a command works without an injected obj (callback builds the real context)
    result = runner.invoke(app, ["session", "ls", "--help"])
    assert result.exit_code == 0


def test_session_command_exposes_real_subcommands() -> None:
    result = runner.invoke(app, ["session", "ls", "--help"])
    assert result.exit_code == 0


def test_bash_wrappers_delegate_their_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    delegated: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        main, "_delegate_to_shim", lambda name, args: delegated.append((name, args))
    )

    for command in ("install", "update", "dock", "profile-shell"):
        result = runner.invoke(app, [command, "--example"], obj=make_fake_context())
        assert result.exit_code == 0

    assert delegated == [
        ("install", ["--example"]),
        ("update", ["--example"]),
        ("dock", ["--example"]),
        ("profile-shell", ["--example"]),
    ]


def test_delegate_execs_the_repository_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(os, "execvp", lambda executable, argv: calls.append((executable, argv)))

    main._delegate_to_shim("dock", ["--example"])

    shim = str(main._SHIM)
    assert calls == [(shim, [shim, "dock", "--example"])]


def test_launch_tui_returns_without_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = type("FakeTui", (), {"handoff_command": None, "run": lambda self: None})()
    monkeypatch.setattr("dotfiles.tui.app.MissionControlApp", lambda: fake)
    monkeypatch.setattr(os, "execvp", lambda *_args: pytest.fail("unexpected handoff"))

    main._launch_tui()


def test_launch_tui_execs_requested_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = type(
        "FakeTui",
        (),
        {"handoff_command": ("zellij", "attach", "work"), "run": lambda self: None},
    )()
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr("dotfiles.tui.app.MissionControlApp", lambda: fake)
    monkeypatch.setattr(os, "execvp", lambda executable, argv: calls.append((executable, argv)))

    main._launch_tui()

    assert calls == [("zellij", ["zellij", "attach", "work"])]


def test_print_help_renders_branded_error(capsys: pytest.CaptureFixture[str]) -> None:
    main.print_help(error="bad command")
    captured = capsys.readouterr()
    assert "bad command" in captured.err
    assert "Machine" in captured.err
