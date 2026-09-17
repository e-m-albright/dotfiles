"""Subprocess smoke tests for the bash shim's routing behavior.

`app/test_command_tree.py` keeps the shim's command lists in sync with the
Typer tree; these lock the shim's own dispatch: unknown commands fail loudly,
help never hard-fails, and the doctor <-> workbench contract verb is real.
"""

import subprocess
from pathlib import Path

import pytest

_SHIM = Path(__file__).resolve().parents[4] / "bin" / "dotfiles"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(_SHIM), *args], capture_output=True, text=True, timeout=60, check=False
    )


def test_unknown_command_exits_nonzero_with_message() -> None:
    result = _run("definitely-not-a-command")
    assert result.returncode != 0
    assert "definitely-not-a-command" in result.stdout + result.stderr


def test_bare_invocation_prints_help_and_exits_zero() -> None:
    result = _run()
    assert result.returncode == 0
    assert "doctor" in result.stdout


def test_bash_native_command_help_never_enters_the_implementation() -> None:
    # `dfs install --help` must show help, not start the installer.
    result = _run("install", "--help")
    assert result.returncode == 0
    assert "install" in result.stdout


def test_workbench_drift_verb_exists_in_real_cli() -> None:
    """Contract check: the verb doctor invokes must exist in workbench's CLI.

    Guards against the shipped `workbench check` bug class: doctor's tests fake
    the workbench CLI, so nothing else validates the verb against reality.
    """
    workbench = Path.home() / "code" / "public" / "workbench" / "bin" / "workbench"
    if not workbench.exists():
        pytest.skip("workbench clone not present on this machine")
    result = subprocess.run(
        [str(workbench), "drift", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
