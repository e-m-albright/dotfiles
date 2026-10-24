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
    "fnm install 26",
    "fnm use --install-if-missing 26",
    "fnm default 26",
    "node --version",
    "rustup update",
    "rustc --version",
    "uv --version",
    "uv python install --upgrade 3.14",
    "npx --yes get-pnpm 12.15.0",
    "dotfiles brew install --profile personal",
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
    'fnm install 26' | 'fnm use --install-if-missing 26' | \
    'fnm default 26' | 'rustup update' | 'dotfiles brew install --profile personal' | \
    'dotfiles brew install --profile work' | 'uv python install --upgrade 3.14' | \
    'npx --yes get-pnpm 12.15.0') ;;
    'fnm env') printf ':\\n' ;;
    'node --version') printf 'v26.12.1\\n' ;;
    'rustc --version') printf 'rustc 1.90.0\\n' ;;
    'uv --version') printf 'uv 0.8.0\\n' ;;
    *) printf 'Unexpected command: %s\\n' "$call" >&2; exit 99 ;;
esac
"""


def _run_update(
    tmp_path: Path, failure: str, profile: str = "personal", args: tuple[str, ...] = ()
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    repo = tmp_path / "repo"
    shim = repo / "bin" / "dotfiles"
    shim.parent.mkdir(parents=True)
    shutil.copy2(_REPO / "bin" / "dotfiles", shim)
    (repo / "scripts/lib").mkdir(parents=True)
    shutil.copy2(_REPO / "scripts/lib/output.sh", repo / "scripts/lib/output.sh")
    shutil.copy2(_REPO / "scripts/lib/host.sh", repo / "scripts/lib/host.sh")
    shutil.copy2(_REPO / "scripts/update.sh", repo / "scripts/update.sh")
    home = tmp_path / "home"
    home.mkdir()
    marker = home / ".config/dotfiles/profile"
    marker.parent.mkdir(parents=True)
    marker.write_text(profile + "\n")
    (repo / "config").mkdir()
    shutil.copy2(_REPO / "config/runtimes.conf", repo / "config/runtimes.conf")
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
        *(
            binaries / name
            for name in ("sudo", "fnm", "node", "rustup", "rustc", "uv", "npm", "npx")
        ),
    ]:
        executable.write_text(_STUB)
        executable.chmod(0o755)
    calls = tmp_path / "calls"
    result = subprocess.run(
        [str(shim), "update", *args],
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
    return result, calls.read_text().splitlines() if calls.exists() else []


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


def test_work_update_does_not_install_personal_tools(tmp_path: Path) -> None:
    result, calls = _run_update(tmp_path, "", profile="work")
    assert result.returncode == 0, result.stderr
    assert "dotfiles brew install --profile work" in calls
    assert "rustup update" not in calls
    assert not any(call.startswith("npx ") for call in calls)


def test_explicit_work_update_overrides_marker_without_changing_it(tmp_path: Path) -> None:
    result, calls = _run_update(tmp_path, "", args=("--profile", "work"))
    assert result.returncode == 0, result.stderr
    assert "dotfiles brew install --profile work" in calls
    assert "rustup update" not in calls
    assert (tmp_path / "home/.config/dotfiles/profile").read_text() == "personal\n"


def test_invalid_profile_fails_before_any_updater(tmp_path: Path) -> None:
    result, calls = _run_update(tmp_path, "", profile="invalid")
    assert result.returncode != 0
    assert calls == []
