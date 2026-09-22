"""Exercise update failures with a disposable shim and no access to host updaters."""

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_STEPS = (
    "sudo softwareupdate -i -a",
    "dotfiles brew upgrade",
    "fnm env",
    "fnm install --lts",
    "fnm use --install-if-missing lts-latest",
    "fnm default lts-latest",
    "node --version",
    "rustup update",
    "rustc --version",
    "uv --version",
    "dotfiles brew install",
)
_STUB = """#!/bin/bash
call="${0##*/} $*"
printf '%s\\n' "$call" >> "$TEST_CALLS"
if [[ "$call" == "$TEST_FAILURE" ]]; then
    printf 'Forced failure: %s\\n' "$call" >&2
    exit 42
fi
case "$call" in
    'sudo softwareupdate -i -a' | 'dotfiles brew upgrade' | \
    'fnm install --lts' | 'fnm use --install-if-missing lts-latest' | \
    'fnm default lts-latest' | 'rustup update' | 'dotfiles brew install') ;;
    'fnm env') printf ':\\n' ;;
    'node --version') printf 'v24.20.0\\n' ;;
    'rustc --version') printf 'rustc 1.90.0\\n' ;;
    'uv --version') printf 'uv 0.8.0\\n' ;;
    *) printf 'Unexpected command: %s\\n' "$call" >&2; exit 99 ;;
esac
"""


def _run_update(tmp_path: Path, failure: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    repo = tmp_path / "repo"
    shim = repo / "bin" / "dotfiles"
    shim.parent.mkdir(parents=True)
    shutil.copy2(_REPO / "bin" / "dotfiles", shim)
    (repo / "macos").mkdir()
    shutil.copy2(_REPO / "macos" / "print_utils.sh", repo / "macos" / "print_utils.sh")
    home = tmp_path / "home"
    home.mkdir()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    # Only pure text/path utilities are admitted. A missing updater cannot reach the host.
    for utility in ("bash", "basename", "dirname", "tail", "awk"):
        executable = shutil.which(utility)
        assert executable
        (binaries / utility).symlink_to(executable)
    cli = repo / "cli" / ".venv" / "bin" / "dotfiles"
    cli.parent.mkdir(parents=True)
    for executable in [
        cli,
        *(binaries / name for name in ("sudo", "fnm", "node", "rustup", "rustc", "uv", "npm")),
    ]:
        executable.write_text(_STUB)
        executable.chmod(0o755)
    calls = tmp_path / "calls"
    result = subprocess.run(
        [str(shim), "update"],
        env={
            "HOME": str(home),
            "PATH": str(binaries),
            "TEST_CALLS": str(calls),
            "TEST_FAILURE": failure,
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result, calls.read_text().splitlines()


@pytest.mark.parametrize("failure", _STEPS)
def test_update_stops_at_failed_step(tmp_path: Path, failure: str) -> None:
    result, calls = _run_update(tmp_path, failure)
    assert result.returncode != 0
    assert "All updates finished" not in result.stdout
    assert calls == list(_STEPS[: _STEPS.index(failure) + 1])


def test_update_reports_completion_after_all_steps_succeed(tmp_path: Path) -> None:
    result, calls = _run_update(tmp_path, "")
    assert result.returncode == 0, result.stderr
    assert "All updates finished" in result.stdout
    assert calls == list(_STEPS)
