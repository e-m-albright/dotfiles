from __future__ import annotations

import os
import subprocess
from pathlib import Path

INSTALLER = Path(__file__).parents[1] / "install.sh"


def test_install_plan_runs_on_linux_without_mutating_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home)}

    result = subprocess.run(
        ["bash", str(INSTALLER), "--plan"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Dotfiles macOS install plan" in result.stdout
    assert "Link tracked shell and Git configuration" in result.stdout
    assert "Reconcile packages from macos/packages.toml" in result.stdout
    assert "Sync and verify Workbench configuration" in result.stdout
    assert list(home.iterdir()) == []


def test_work_install_plan_enumerates_allowlist_and_skipped_mutations(tmp_path: Path) -> None:
    env = {**os.environ, "HOME": str(tmp_path)}
    result = subprocess.run(
        ["bash", str(INSTALLER), "--plan", "--profile", "work"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    for software in (
        "git-lfs",
        "tenv",
        "ghostty",
        "orbstack",
        "claude_code",
        "@earendil-works/pi-coding-agent",
    ):
        assert software in result.stdout
    assert "Skipped host mutations" in result.stdout
    assert "Zed settings" in result.stdout
    assert "Go and Rust tools" in result.stdout
    assert "hashicorp/tap" not in result.stdout
    assert "docker-compose" not in result.stdout
    assert "shared shell configuration" in result.stdout


def test_native_pnpm_uses_the_global_prefix_not_its_bin_directory() -> None:
    installer = INSTALLER.read_text()

    assert 'PNPM_HOME="$HOME/.npm-global" npx --yes get-pnpm 12.1.0' in installer
    assert 'PNPM_HOME="$HOME/.npm-global/bin" npx --yes get-pnpm' not in installer


def test_private_automation_discovery_ignores_linked_worktrees() -> None:
    installer = INSTALLER.read_text()

    assert '[[ -x "$candidate" && -d "${candidate%/bin/notes}/.git" ]]' in installer


def test_install_rejects_unknown_arguments_before_host_checks(tmp_path: Path) -> None:
    env = {**os.environ, "HOME": str(tmp_path)}
    result = subprocess.run(
        [
            "bash",
            "-c",
            'OSTYPE=linux-gnu; source "$1" --unknown',
            "install-plan-test",
            str(INSTALLER),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 2
    assert "Usage: install.sh [--plan] [--profile personal|work]" in result.stderr
