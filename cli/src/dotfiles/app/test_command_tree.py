"""Contract checks for the hybrid Bash/Typer command tree."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from dotfiles.app.main import PANEL_CONTROL, PANEL_MACHINE, app

_REPO = Path(__file__).resolve().parents[4]
_SHIM = _REPO / "bin" / "dotfiles"
_COMPLETIONS = _REPO / "shell" / "completions" / "_dotfiles"
_BASH_NATIVE = {"install", "update", "dock", "profile-shell"}
_PANELS = {PANEL_MACHINE, PANEL_CONTROL}


def _routed_commands() -> set[str]:
    match = re.search(r'PY_CLI_COMMANDS="([^"]*)"', _SHIM.read_text(encoding="utf-8"))
    assert match, "PY_CLI_COMMANDS assignment not found in bin/dotfiles"
    return set(match.group(1).split())


def _registered() -> dict[str, str | None]:
    names: dict[str, str | None] = {}
    for command in app.registered_commands:
        name = command.name or (
            command.callback.__name__.replace("_", "-") if command.callback else None
        )
        assert name
        names[name] = command.rich_help_panel
    for group in app.registered_groups:
        assert group.name
        names[group.name] = group.rich_help_panel
    return names


def test_every_command_is_routed_registered_and_completable() -> None:
    routed = _routed_commands()
    registered = _registered()
    completions = _COMPLETIONS.read_text(encoding="utf-8")

    assert not (routed - registered.keys())
    assert not {name for name in routed if name not in completions}
    assert not (registered.keys() - routed - _BASH_NATIVE)
    assert not (_BASH_NATIVE - registered.keys())


def test_every_top_level_command_uses_a_known_panel() -> None:
    assert not {name: panel for name, panel in _registered().items() if panel not in _PANELS}


def test_native_help_lists_active_commands_only() -> None:
    result = subprocess.run([str(_SHIM), "--help"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    for command in ("doctor", "brew", "remote", "password"):
        assert command in result.stdout
    for retired in ("session", "tui", "email-mask"):
        assert retired not in result.stdout


def test_unknown_command_reports_error_and_native_help() -> None:
    result = subprocess.run(
        [str(_SHIM), "not-a-command"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 2
    assert "not-a-command" in result.stderr
    assert "Usage:" in result.stderr


def test_bash_native_help_never_enters_implementation() -> None:
    for command in sorted(_BASH_NATIVE):
        for flag in ("--help", "-h"):
            result = subprocess.run(
                [str(_SHIM), command, flag], capture_output=True, text=True, check=False
            )
            assert result.returncode == 0
            assert "Usage:" in result.stdout
            assert command in result.stdout


def test_bash_native_commands_reject_arguments_before_execution() -> None:
    for command in sorted(_BASH_NATIVE):
        result = subprocess.run(
            [str(_SHIM), command, "unexpected"], capture_output=True, text=True, check=False
        )
        assert result.returncode == 2
        assert "accepts no arguments" in result.stderr
