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
from pathlib import Path

from dotfiles.app.main import PANEL_AI, PANEL_CONTROL, PANEL_MACHINE, app

_REPO = Path(__file__).resolve().parents[4]
_SHIM = _REPO / "bin" / "dotfiles"
_COMPLETIONS = _REPO / "shell" / "completions" / "_dotfiles"

_PANELS = {PANEL_MACHINE, PANEL_CONTROL, PANEL_AI}


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


def test_every_top_level_command_is_grouped_into_a_known_panel() -> None:
    """Nothing may fall into Typer's default 'Commands' panel — that would break
    the Machine/Control/AI grouping the unified help relies on."""
    ungrouped = {name: panel for name, panel in _registered().items() if panel not in _PANELS}
    assert not ungrouped, f"top-level commands outside a known help panel: {ungrouped}"
