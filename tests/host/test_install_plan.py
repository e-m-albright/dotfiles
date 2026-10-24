from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALLER = (
    next(parent for parent in Path(__file__).resolve().parents if (parent / "AGENTS.md").is_file())
    / "install.sh"
)


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
    assert "Reconcile packages from config/packages.toml" in result.stdout
    assert "Sync and verify Workbench configuration" in result.stdout
    assert list(home.iterdir()) == []


def test_work_install_plan_enumerates_allowlist_and_skipped_mutations(
    tmp_path: Path,
) -> None:
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
        "rectangle",
        "flycut",
        "ghostty",
        "caffeine",
        "flux-app",
        "typewhisper",
        "orbstack",
        "claude-code",
        "@earendil-works/pi-coding-agent",
    ):
        assert software in result.stdout
    assert "Skipped host mutations" in result.stdout
    assert "Zed settings" in result.stdout
    assert "Go and Rust tools" in result.stdout
    assert "hashicorp/tap" not in result.stdout
    assert "docker-compose" not in result.stdout
    assert "shared shell configuration" in result.stdout


@pytest.mark.parametrize("python_available", [True, False])
def test_work_plan_reads_manifest_and_runtime_changes_without_brew_or_uv(
    tmp_path: Path,
    python_available: bool,
) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(INSTALLER.parent / "config", repo / "config")
    shutil.copytree(INSTALLER.parent / "scripts", repo / "scripts")
    shutil.copytree(INSTALLER.parent / "bin", repo / "bin")
    shutil.copyfile(INSTALLER, repo / "install.sh")
    manifest = repo / "config/packages.toml"
    manifest.write_text(
        manifest.read_text().replace(
            'formulae = [\n  "git",', 'formulae = [\n  "plan-only-sentinel", "git",'
        )
    )
    (repo / "config/runtimes.conf").write_text(
        "NODE_VERSION=99\nPYTHON_VERSION=3.99\nPNPM_VERSION=99.1.0\n"
    )
    home = tmp_path / "home"
    home.mkdir()
    commands = tmp_path / "commands"
    commands.mkdir()
    names = (
        ("bash", "dirname", "cat", "python3") if python_available else ("bash", "dirname", "cat")
    )
    for name in names:
        executable = shutil.which(name)
        assert executable
        (commands / name).symlink_to(executable)
    result = subprocess.run(
        ["/bin/bash", str(repo / "install.sh"), "--plan", "--profile", "work"],
        env={"HOME": str(home), "PATH": str(commands)},
        capture_output=True,
        text=True,
        check=False,
    )
    if python_available:
        assert result.returncode == 0, result.stderr
        assert "plan-only-sentinel" in result.stdout
        assert "Node.js 99" in result.stdout
        assert "Python 3.99" in result.stdout
    else:
        assert result.returncode != 0
        assert "requires an existing Python 3.11+ with tomllib" in result.stderr
    assert list(home.iterdir()) == []


def test_workbench_clone_stays_attached_to_main() -> None:
    installer = (INSTALLER.parent / "scripts/install.sh").read_text()

    assert "checkout --detach" not in installer
    assert installer.count('checkout -B main "$WORKBENCH_COMMIT"') == 1
    assert 'attach_workbench_main "$directory"' in installer


def test_native_pnpm_uses_the_global_prefix_not_its_bin_directory() -> None:
    installer = (INSTALLER.parent / "scripts/install.sh").read_text()

    assert 'PNPM_HOME="$HOME/.npm-global" npx --yes get-pnpm "$PNPM_VERSION"' in installer
    assert 'PNPM_HOME="$HOME/.npm-global/bin" npx --yes get-pnpm' not in installer


def test_private_automation_discovery_ignores_linked_worktrees() -> None:
    installer = (INSTALLER.parent / "scripts/install.sh").read_text()

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
