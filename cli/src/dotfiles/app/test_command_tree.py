"""Contract-drift gate for the `bin/dotfiles` command tree.

The shim is a hybrid dispatcher: some commands route to the Python CLI
(`PY_CLI_COMMANDS`), others stay Bash-native. The help text (`sub_help`) and the
zsh completion file (`shell/completions/_dotfiles`) are hand-maintained for UX,
so they can silently fall out of sync with the routed-command list. This test
fails the moment a routed command is missing from either, turning silent drift
into a caught error (philosophy principle #3).
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_SHIM = _REPO / "bin" / "dotfiles"
_COMPLETIONS = _REPO / "shell" / "completions" / "_dotfiles"


def _shim_text() -> str:
    return _SHIM.read_text(encoding="utf-8")


def _routed_commands(text: str) -> set[str]:
    """Extract the command names from the PY_CLI_COMMANDS=" a b c " line."""
    match = re.search(r'PY_CLI_COMMANDS="([^"]*)"', text)
    assert match, "PY_CLI_COMMANDS assignment not found in bin/dotfiles"
    return set(match.group(1).split())


def _section(text: str, func_name: str) -> str:
    """Return the body of a `func_name () { ... }` shell function."""
    start = text.index(f"{func_name} ")
    depth = 0
    started = False
    for i in range(text.index("{", start), len(text)):
        if text[i] == "{":
            depth += 1
            started = True
        elif text[i] == "}":
            depth -= 1
            if started and depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"could not find body of {func_name}")


def test_every_routed_command_is_documented_in_help_and_completions() -> None:
    text = _shim_text()
    routed = _routed_commands(text)
    help_body = _section(text, "sub_help")
    completions_body = _COMPLETIONS.read_text(encoding="utf-8")

    missing_from_help = {c for c in routed if c not in help_body}
    missing_from_completions = {c for c in routed if c not in completions_body}

    assert not missing_from_help, f"PY_CLI_COMMANDS missing from sub_help: {missing_from_help}"
    assert not missing_from_completions, (
        f"PY_CLI_COMMANDS missing from shell/completions/_dotfiles: {missing_from_completions}"
    )
