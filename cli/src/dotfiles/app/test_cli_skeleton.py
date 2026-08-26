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
    for command in ("remote", "doctor", "brew", "password"):
        assert command in result.output
    assert "session" not in result.output
    assert "email-mask" not in result.output
    assert "tui" not in result.output


def test_root_callback_builds_context_when_none_injected() -> None:
    # a command works without an injected obj (callback builds the real context)
    result = runner.invoke(app, ["remote", "status", "--help"])
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
