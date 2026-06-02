"""Contract-drift gate for the `bin/dotfiles` command tree.

The shim is a hybrid dispatcher: some commands route to the Python CLI
(`PY_CLI_COMMANDS`), others stay Bash-native. The help text (`sub_help`) and the
shell completions (`sub_completions`) are hand-maintained for UX, so they can
silently fall out of sync with the routed-command list — exactly how `version`
once went undocumented. This test fails the moment a routed command is missing
from either, turning silent drift into a caught error (philosophy principle #3).
"""

from __future__ import annotations

import re
from pathlib import Path

_SHIM = Path(__file__).resolve().parents[4] / "bin" / "dotfiles"


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
    completions_body = _section(text, "sub_completions")

    missing_from_help = {c for c in routed if c not in help_body}
    missing_from_completions = {c for c in routed if c not in completions_body}

    assert not missing_from_help, f"PY_CLI_COMMANDS missing from sub_help: {missing_from_help}"
    assert not missing_from_completions, (
        f"PY_CLI_COMMANDS missing from sub_completions: {missing_from_completions}"
    )


def test_version_is_documented() -> None:
    """Regression guard for the specific command that had drifted."""
    text = _shim_text()
    assert "version" in _routed_commands(text)
    assert "version" in _section(text, "sub_help")
    assert "version" in _section(text, "sub_completions")
