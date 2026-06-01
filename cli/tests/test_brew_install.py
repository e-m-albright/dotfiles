"""Tests for brew install execution functions in core/brew.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.core.brew import (
    _TW_DMG_PATH,
    _TW_FETCH_URL,
    PackageManifest,
    add_taps,
    install_claude_code,
    install_npm_globals,
    install_packages,
    install_rust,
    install_typewhisper,
)
from tests.fakes import FakeProcessRunner

# ---------------------------------------------------------------------------
# Minimal TOML fixture
# ---------------------------------------------------------------------------

INSTALL_TOML = """\
[flags]
ai = true
productivity = true
social = true

[taps]
list = ["ariga/tap", "infisical/get-cli"]

[[section]]
name = "Core CLI"
kind = "formula"
packages = [
  { name = "git" },
  { name = "jq" },
]

[[section]]
name = "Casks"
kind = "cask"
packages = [
  { name = "ghostty" },
  { name = "obsidian" },
]

[[section]]
name = "AI Tools"
kind = "auto"
flag = "ai"
packages = [
  { name = "claude" },
]

[[npm_package]]
name = "wrangler"
note = "Cloudflare Workers CLI"

[[npm_package]]
name = "agent-browser"
flag = "ai"
note = "Browser automation"
"""


def make_toml(tmp_path: Path, content: str = INSTALL_TOML) -> Path:
    p = tmp_path / "packages.toml"
    p.write_text(content)
    return p


def load(tmp_path: Path, content: str = INSTALL_TOML) -> PackageManifest:
    return PackageManifest.load(make_toml(tmp_path, content))


# ---------------------------------------------------------------------------
# add_taps
# ---------------------------------------------------------------------------


def test_add_taps_success(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "tap", "ariga/tap"), exit_code=0)
    runner.script(("brew", "tap", "infisical/get-cli"), exit_code=0)

    results = add_taps(manifest, runner)
    assert len(results) == 2
    assert all(r.level == "success" for r in results)
    assert ("brew", "tap", "ariga/tap") in runner.calls
    assert ("brew", "tap", "infisical/get-cli") in runner.calls


def test_add_taps_error(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "tap", "ariga/tap"), exit_code=1, stderr="network error")
    runner.script(("brew", "tap", "infisical/get-cli"), exit_code=0)

    results = add_taps(manifest, runner)
    levels = [r.level for r in results]
    # A failed tap is tolerant (warn), not a hard error that aborts the install.
    assert "warn" in levels
    assert "success" in levels
    assert "error" not in levels


def test_add_taps_empty(tmp_path: Path) -> None:
    toml = INSTALL_TOML.replace('list = ["ariga/tap", "infisical/get-cli"]', "list = []")
    manifest = load(tmp_path, toml)
    runner = FakeProcessRunner()
    results = add_taps(manifest, runner)
    assert results == []
    assert runner.calls == []


# ---------------------------------------------------------------------------
# install_packages — formula vs cask vs auto
# ---------------------------------------------------------------------------


def _scripted_runner_some_installed() -> FakeProcessRunner:
    """git installed as formula; ghostty installed as cask; jq, obsidian, claude missing."""
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="ghostty\n")
    return runner


def test_install_packages_only_missing(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = _scripted_runner_some_installed()

    install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})

    # Only jq (formula), obsidian (cask), claude (auto) should be installed
    install_calls = [c for c in runner.calls if "install" in c and "list" not in c]
    installed_names = {c[-1] for c in install_calls}
    assert "jq" in installed_names
    assert "obsidian" in installed_names
    assert "claude" in installed_names
    # Already-installed ones must not be reinstalled
    assert "git" not in installed_names
    assert "ghostty" not in installed_names


def test_install_packages_formula_command(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\n")  # git installed
    runner.script(
        ("brew", "list", "--cask", "-1"), stdout="ghostty\nobsidian\nclaude\n"
    )  # casks installed

    install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    # Only jq is missing (formula)
    assert ("brew", "install", "jq") in runner.calls
    # cask command must NOT be used for formula kind
    assert ("brew", "install", "--cask", "jq") not in runner.calls


def test_install_packages_cask_command(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\njq\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="ghostty\nclaude\n")  # obsidian missing

    install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    assert ("brew", "install", "--cask", "obsidian") in runner.calls


def test_install_packages_auto_tries_formula_first(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\njq\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="ghostty\nobsidian\n")
    # claude (auto kind) is missing — formula install succeeds

    install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    assert ("brew", "install", "claude") in runner.calls


def test_install_packages_auto_falls_back_to_cask(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\njq\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="ghostty\nobsidian\n")
    # claude formula fails → should try cask
    runner.script(("brew", "install", "claude"), exit_code=1)

    install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    assert ("brew", "install", "--cask", "claude") in runner.calls


def test_install_packages_dry_run_no_mutating_calls(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")

    results = install_packages(
        manifest, runner, flags_on={"ai", "productivity", "social"}, dry_run=True
    )
    # Only brew list calls should have been made
    mutating = [c for c in runner.calls if "install" in c and "list" not in c]
    assert mutating == []
    # Results should all be info (DRY RUN messages)
    assert all(r.level == "info" for r in results)


def test_install_packages_all_installed_reports_info(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\njq\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="ghostty\nobsidian\nclaude\n")

    results = install_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    assert len(results) == 1
    assert results[0].level == "info"


def test_install_packages_respects_flag_gating(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")

    # ai OFF → claude must not be installed
    install_packages(manifest, runner, flags_on={"productivity", "social"})
    install_calls = [c for c in runner.calls if "install" in c and "list" not in c]
    installed_names = {c[-1] for c in install_calls}
    assert "claude" not in installed_names


# ---------------------------------------------------------------------------
# install_rust
# ---------------------------------------------------------------------------


def test_install_rust_skips_when_present(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("sh", "-c", "command -v rustup || command -v cargo"),
        stdout="/usr/bin/cargo\n",
    )
    results = install_rust(runner, home=tmp_path)
    assert len(results) == 1
    assert results[0].level == "info"
    assert "already installed" in results[0].message
    # Must not run the rustup installer
    assert not any("rustup.rs" in " ".join(c) for c in runner.calls)


def test_install_rust_runs_installer_when_absent(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v rustup || command -v cargo"), stdout="")
    runner.script(
        (
            "sh",
            "-c",
            "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
        ),
        exit_code=0,
    )
    # Create a tmp .zprofile so the append path can write to it
    zprofile = tmp_path / ".zprofile"
    zprofile.write_text("")
    results = install_rust(runner, home=tmp_path)
    assert any("rustup.rs" in " ".join(c) for c in runner.calls)
    assert results[0].level == "success"
    # The TMP zprofile (not the real one) received the cargo line
    assert ".cargo/env" in zprofile.read_text()


def test_install_rust_error_on_install_failure(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v rustup || command -v cargo"), stdout="")
    runner.script(
        (
            "sh",
            "-c",
            "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
        ),
        exit_code=1,
        stderr="network error",
    )
    results = install_rust(runner, home=tmp_path)
    assert results[0].level == "error"


# ---------------------------------------------------------------------------
# install_claude_code
# ---------------------------------------------------------------------------


def test_install_claude_code_skips_when_present() -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v claude"), stdout="/usr/local/bin/claude\n")
    results = install_claude_code(runner)
    assert results[0].level == "info"
    assert "already installed" in results[0].message
    assert not any("claude.ai" in " ".join(c) for c in runner.calls)


def test_install_claude_code_runs_installer() -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v claude"), stdout="")
    runner.script(
        ("sh", "-c", "curl -fsSL https://claude.ai/install.sh | bash"),
        exit_code=0,
    )
    results = install_claude_code(runner)
    assert any("claude.ai" in " ".join(c) for c in runner.calls)
    assert results[0].level == "success"


def test_install_claude_code_error_on_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v claude"), stdout="")
    runner.script(
        ("sh", "-c", "curl -fsSL https://claude.ai/install.sh | bash"),
        exit_code=1,
        stderr="download failed",
    )
    results = install_claude_code(runner)
    assert results[0].level == "error"


# ---------------------------------------------------------------------------
# install_typewhisper
# ---------------------------------------------------------------------------

# The fetch-URL shell command and DMG path are imported from core/brew.py so
# tests script exactly the same tuple the implementation passes to runner.run().
_TW_FETCH_CMD = _TW_FETCH_URL  # tuple[str, str, str] — (sh, -c, <shell>)


def test_install_typewhisper_skips_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch Path.exists so /Applications/TypeWhisper.app looks present
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/Applications/TypeWhisper.app")
    runner = FakeProcessRunner()
    results = install_typewhisper(runner)
    assert results[0].level == "info"
    assert "already installed" in results[0].message
    assert runner.calls == []


def test_install_typewhisper_no_url_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    runner = FakeProcessRunner()
    runner.script(_TW_FETCH_CMD, stdout="")
    results = install_typewhisper(runner)
    assert results[0].level == "error"
    assert "no stable DMG" in results[0].message


def test_install_typewhisper_full_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    runner = FakeProcessRunner()
    tw_url = "https://github.com/TypeWhisper/typewhisper-mac/releases/download/v1.0/TypeWhisper.dmg"
    runner.script(_TW_FETCH_CMD, stdout=tw_url + "\n")
    runner.script(
        ("curl", "-fsSL", "-o", _TW_DMG_PATH, tw_url),
        exit_code=0,
    )
    _mount_cmd = (
        f"hdiutil attach {_TW_DMG_PATH!r} -nobrowse -noautoopen 2>/dev/null"
        " | grep -oE '/Volumes/.*' | tail -1"
    )
    runner.script(
        ("sh", "-c", _mount_cmd),
        stdout="/Volumes/TypeWhisper\n",
    )
    runner.script(
        ("cp", "-R", "/Volumes/TypeWhisper/TypeWhisper.app", "/Applications/"),
        exit_code=0,
    )
    results = install_typewhisper(runner)
    assert results[0].level == "success"
    assert "TypeWhisper installed" in results[0].message


# ---------------------------------------------------------------------------
# install_npm_globals
# ---------------------------------------------------------------------------


def test_install_npm_globals_skips_present(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    # Both wrangler and agent-browser are already installed
    runner.script(("sh", "-c", "command -v wrangler"), stdout="/usr/local/bin/wrangler\n")
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="/usr/local/bin/agent-browser\n")

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    npm_calls = [c for c in runner.calls if c[0] == "npm"]
    assert npm_calls == []
    assert all(r.level == "info" for r in results)


def test_install_npm_globals_installs_missing(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v wrangler"), stdout="", exit_code=1)
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="", exit_code=1)

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    assert ("npm", "install", "-g", "wrangler") in runner.calls
    assert ("npm", "install", "-g", "agent-browser") in runner.calls
    assert all(r.level == "success" for r in results)


def test_install_npm_globals_flag_gates_ai_packages(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v wrangler"), stdout="", exit_code=1)

    # ai OFF → agent-browser should NOT be installed
    install_npm_globals(manifest, runner, flags_on=set())
    npm_calls = [c for c in runner.calls if c[0] == "npm"]
    installed_names = {c[-1] for c in npm_calls}
    assert "agent-browser" not in installed_names
    assert "wrangler" in installed_names


def test_install_npm_globals_error_on_failure(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v wrangler"), stdout="", exit_code=1)
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="", exit_code=1)
    runner.script(("npm", "install", "-g", "wrangler"), exit_code=1)

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    levels = [r.level for r in results]
    assert "error" in levels
