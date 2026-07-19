"""Contract-drift gate for the `bin/dotfiles` command tree.

The shim is a hybrid dispatcher: some commands route to the Python CLI
(`PY_CLI_COMMANDS`), others stay Bash-native but are still registered as thin
wrappers in the Typer app so a single renderer draws all help. Top-level help is
now generated from the Typer app (`dotfiles.app.main.print_help`), so the catalog
lives in exactly one place; the zsh completion file is still hand-maintained for
UX and can silently fall out of sync. This test fails the moment a routed command
is missing from the Typer app or the completions, and the moment any top-level
command lands outside a known Rich help panel (which would render it un-grouped).
"""

from __future__ import annotations

import re
import subprocess
from io import StringIO
from pathlib import Path

from rich.console import Console

from dotfiles.app.main import PANEL_CONTROL, PANEL_MACHINE, app, render_help_tree

_REPO = Path(__file__).resolve().parents[4]
_SHIM = _REPO / "bin" / "dotfiles"
_COMPLETIONS = _REPO / "shell" / "completions" / "_dotfiles"

_PANELS = {PANEL_MACHINE, PANEL_CONTROL}

# Top-level commands the shim handles natively in Bash (the `case` arms + the
# Bash `case` arms, so they are registered in the Typer app for help/rendering
# but intentionally absent from PY_CLI_COMMANDS. Every other registered command MUST
# be routed to the Python CLI — see test_every_registered_command_is_reachable.
_BASH_NATIVE = {"install", "update", "clean", "dock", "profile-shell"}


def _routed_commands() -> set[str]:
    """Extract the command names from the PY_CLI_COMMANDS=" a b c " shim line."""
    match = re.search(r'PY_CLI_COMMANDS="([^"]*)"', _SHIM.read_text(encoding="utf-8"))
    assert match, "PY_CLI_COMMANDS assignment not found in bin/dotfiles"
    return set(match.group(1).split())


def _registered() -> dict[str, str | None]:
    """Map every top-level Typer command/group name to its Rich help-panel title."""
    names: dict[str, str | None] = {}
    for cmd in app.registered_commands:
        name = cmd.name or (cmd.callback.__name__.replace("_", "-") if cmd.callback else None)
        assert name, f"command without a resolvable name: {cmd!r}"
        names[name] = cmd.rich_help_panel
    for group in app.registered_groups:
        assert group.name, f"group without a name: {group!r}"
        names[group.name] = group.rich_help_panel
    return names


def test_every_routed_command_is_registered_and_completable() -> None:
    routed = _routed_commands()
    registered = _registered()
    completions = _COMPLETIONS.read_text(encoding="utf-8")

    missing_from_app = routed - registered.keys()
    missing_from_completions = {c for c in routed if c not in completions}

    assert not missing_from_app, f"PY_CLI_COMMANDS missing from the Typer app: {missing_from_app}"
    assert not missing_from_completions, (
        f"PY_CLI_COMMANDS missing from shell/completions/_dotfiles: {missing_from_completions}"
    )


def test_every_registered_command_is_reachable() -> None:
    """The hole this closes: a command registered in the Typer app (so it shows in help)
    but absent from PY_CLI_COMMANDS is rejected by the shim as 'not a known command'.
    Every registered top-level command must be routed to Python or be Bash-native."""
    registered = _registered().keys()
    reachable = _routed_commands() | _BASH_NATIVE
    unreachable = registered - reachable
    assert not unreachable, (
        f"registered but unroutable via bin/dotfiles (add to PY_CLI_COMMANDS or _BASH_NATIVE): "
        f"{unreachable}"
    )


def test_bash_native_commands_are_registered() -> None:
    """Guard the other direction: a stale _BASH_NATIVE entry no longer in the app."""
    stale = _BASH_NATIVE - _registered().keys()
    assert not stale, f"_BASH_NATIVE names no longer registered in the Typer app: {stale}"


def test_every_top_level_command_is_grouped_into_a_known_panel() -> None:
    """Nothing may fall into Typer's default 'Commands' panel — that would break
    the Machine/Control/AI grouping the unified help relies on."""
    ungrouped = {name: panel for name, panel in _registered().items() if panel not in _PANELS}
    assert not ungrouped, f"top-level commands outside a known help panel: {ungrouped}"


def _render() -> str:
    """Render the branded top-level help to a string at a fixed width."""
    console = Console(file=StringIO(), force_terminal=False, width=120)
    render_help_tree(console)
    return console.file.getvalue()  # type: ignore[attr-defined]


def test_top_level_help_nests_every_sub_apps_subcommands() -> None:
    """The whole point of the custom renderer: a group's subcommands are visible on
    the front door, not hidden behind one row. Sample one subcommand per sub-app —
    each is reachable only as `dfs <group> <sub>`, so its presence proves nesting."""
    out = _render()
    for hidden_subcommand in ("status", "stale", "attach", "deactivate"):
        assert hidden_subcommand in out, f"{hidden_subcommand!r} missing from the nested help tree"


def test_subcommands_render_under_their_parent_group() -> None:
    """Nested commands appear after their parent group."""
    out = _render()
    assert out.index("brew") < out.index("stale")
    assert out.index("email-mask") < out.index("deactivate")


def test_unknown_shim_command_uses_branded_visual_error() -> None:
    result = subprocess.run(
        [str(_SHIM), "not-a-command"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "╭─ Error" in result.stderr
    assert "not-a-command" in result.stderr
    assert "Machine" in result.stderr
    assert "\033[" not in result.stderr


def test_removed_shell_profile_aliases_stay_removed() -> None:
    for alias in (("shell", "profile"), ("shell_profile",)):
        result = subprocess.run(
            [str(_SHIM), *alias],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        assert "not a known command" in result.stderr


def test_bash_native_help_is_safe_and_consistent() -> None:
    for command in sorted(_BASH_NATIVE):
        for flag in ("--help", "-h"):
            result = subprocess.run(
                [str(_SHIM), command, flag],
                capture_output=True,
                text=True,
                check=False,
            )

            assert result.returncode == 0, (command, flag, result.stderr)
            assert "Usage:" in result.stdout, (command, flag)
            assert command in result.stdout, (command, flag)


def test_bash_native_commands_reject_unexpected_arguments_before_execution() -> None:
    for command in sorted(_BASH_NATIVE):
        result = subprocess.run(
            [str(_SHIM), command, "unexpected"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 2, (command, result.stderr)
        assert "╭─ Error" in result.stderr, command
        assert "accepts no arguments" in result.stderr, command
