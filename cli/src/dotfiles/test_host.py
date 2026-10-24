"""Shared host declarations and fail-closed profile selection."""

import subprocess
from pathlib import Path

import pytest

from dotfiles.host import REPO_ROOT, RuntimeVersions, managed_links, resolve_profile


def test_profile_defaults_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.delenv("DOTFILES_PROFILE", raising=False)
    assert resolve_profile(tmp_path) == "personal"
    marker = tmp_path / ".config/dotfiles/profile"
    marker.parent.mkdir(parents=True)
    marker.write_text("work\n")
    monkeypatch.setenv("DOTFILES_PROFILE", "personal")
    assert resolve_profile(tmp_path) == "work"
    assert resolve_profile(tmp_path, "personal") == "personal"


def test_profile_environment_and_invalid_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTFILES_PROFILE", "work")
    assert resolve_profile(tmp_path) == "work"
    marker = tmp_path / ".config/dotfiles/profile"
    marker.parent.mkdir(parents=True)
    marker.write_text("typo\n")
    with pytest.raises(ValueError, match="profile"):
        resolve_profile(tmp_path)


@pytest.mark.parametrize(
    ("marker", "environment", "expected"),
    [
        (None, "work", "work"),
        ("work\n", "personal", "work"),
        ("personal\n", "work", "personal"),
        (" work \n", "personal", None),
        ("\n", "personal", None),
        (None, "", None),
    ],
)
def test_shell_and_python_resolve_the_same_profile(
    tmp_path, monkeypatch, marker, environment, expected
):
    monkeypatch.setenv("DOTFILES_PROFILE", environment)
    if marker is not None:
        path = tmp_path / ".config/dotfiles/profile"
        path.parent.mkdir(parents=True)
        path.write_text(marker)
    shell = subprocess.run(
        [
            "/bin/bash",
            "-ec",
            'source "$1"; resolve_host_profile; printf "%s" "$PROFILE"',
            "test",
            str(REPO_ROOT / "scripts/lib/host.sh"),
        ],
        env={"HOME": str(tmp_path), "DOTFILES_PROFILE": environment},
        capture_output=True,
        text=True,
        check=False,
    )
    if expected is None:
        assert shell.returncode != 0
        with pytest.raises(ValueError, match="Invalid host profile"):
            resolve_profile(tmp_path)
    else:
        assert shell.returncode == 0, shell.stderr
        assert shell.stdout == resolve_profile(tmp_path) == expected


def test_runtime_declarations_are_strict(tmp_path: Path):
    config = tmp_path / "runtimes.conf"
    config.write_text("NODE_VERSION=28\nPYTHON_VERSION=3.15\nPNPM_VERSION=13.1.0\n")
    versions = RuntimeVersions.load(config)
    assert (versions.node, versions.python, versions.pnpm) == ("28", "3.15", "13.1.0")
    config.write_text("NODE_VERSION=$(whoami)\n")
    with pytest.raises(ValueError, match="runtime"):
        RuntimeVersions.load(config)


@pytest.mark.parametrize("contents", ["", "NODE_VERSION=26\nNODE_VERSION=26\n", "EXTRA=1\n"])
def test_missing_duplicate_and_unknown_runtime_fields_are_rejected(tmp_path, contents):
    config = tmp_path / "runtimes.conf"
    config.write_text(contents)
    with pytest.raises(ValueError, match="runtime"):
        RuntimeVersions.load(config)


def test_link_inventory_is_complete_unique_and_points_to_tracked_sources():
    links = managed_links()
    assert len({link.destination for link in links}) == len(links)
    assert all((REPO_ROOT / link.source).is_file() for link in links)
    assert all(set(link.profiles) <= {"personal", "work"} for link in links)
    personal_only = {link.destination for link in links if "work" not in link.profiles}
    assert {".gitconfig", ".config/zed/settings.json"} <= personal_only
