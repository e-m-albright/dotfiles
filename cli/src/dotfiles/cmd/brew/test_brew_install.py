"""Tests for Brew installation effects."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.cmd.brew.service import (
    _CLAUDE_CODE_SHA256,
    _CLAUDE_CODE_URL,
    _RUSTUP_SHA256,
    _RUSTUP_URL,
    _TW_FETCH_URL,
    PackageManifest,
    add_taps,
    install_claude_code,
    install_go_tools,
    install_npm_globals,
    install_packages,
    install_rust,
    install_typewhisper,
    upgrade,
)
from dotfiles.testing.fakes import FakeProcessRunner

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
version = "4.112.0"
note = "Cloudflare Workers CLI"

[[npm_package]]
name = "agent-browser"
flag = "ai"
note = "Browser automation"

[[npm_package]]
name = "pinchtab"
flag = "ai"
note = "Browser automation (retired)"
disabled = true
reason = "experiment"
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


def test_add_taps_dry_run_reports_without_mutating(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    results = add_taps(load(tmp_path), runner, dry_run=True)
    assert runner.calls == []
    assert all("DRY RUN: brew tap" in step.message for step in results)


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


def test_install_rust_skips_when_present() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("sh", "-c", "command -v rustup || command -v cargo"),
        stdout="/usr/bin/cargo\n",
    )
    results = install_rust(runner)
    assert len(results) == 1
    assert results[0].level == "info"
    assert "already installed" in results[0].message
    # Must not run the rustup installer
    assert not any("rustup.rs" in " ".join(c) for c in runner.calls)


def test_install_rust_runs_installer_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v rustup || command -v cargo"), stdout="")
    install_dir = tmp_path / "rustup"
    install_dir.mkdir()
    monkeypatch.setattr("dotfiles.cmd.brew.service.mkdtemp", lambda *, prefix: str(install_dir))
    installer = install_dir / "rustup-init"
    runner.script(("curl", "-fsSL", "-o", str(installer), _RUSTUP_URL))
    runner.script((str(installer), "-y"))
    # A tracked .zprofile may be symlinked into HOME; installation must not mutate it.
    zprofile = tmp_path / ".zprofile"
    zprofile.write_text("# tracked\n")
    results = install_rust(runner)
    assert ("shasum", "-a", "256", "-c", "-") in runner.calls
    assert f"{_RUSTUP_SHA256}  {installer}\n" in runner.inputs
    assert results[0].level == "success"
    # The TMP zprofile (not the real one) received the cargo line
    assert zprofile.read_text() == "# tracked\n"


def test_install_rust_error_on_install_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v rustup || command -v cargo"), stdout="")
    install_dir = tmp_path / "rustup"
    install_dir.mkdir()
    monkeypatch.setattr("dotfiles.cmd.brew.service.mkdtemp", lambda *, prefix: str(install_dir))
    installer = install_dir / "rustup-init"
    runner.script(("curl", "-fsSL", "-o", str(installer), _RUSTUP_URL), exit_code=1)
    results = install_rust(runner)
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


def test_install_claude_code_runs_installer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v claude"), stdout="")
    install_dir = tmp_path / "claude"
    install_dir.mkdir()
    monkeypatch.setattr("dotfiles.cmd.brew.service.mkdtemp", lambda *, prefix: str(install_dir))
    installer = install_dir / "install.sh"
    runner.script(("curl", "-fsSL", "-o", str(installer), _CLAUDE_CODE_URL))
    results = install_claude_code(runner)
    assert ("bash", str(installer)) in runner.calls
    assert f"{_CLAUDE_CODE_SHA256}  {installer}\n" in runner.inputs
    assert results[0].level == "success"


def test_install_claude_code_error_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeProcessRunner()
    runner.script(("sh", "-c", "command -v claude"), stdout="")
    install_dir = tmp_path / "claude"
    install_dir.mkdir()
    monkeypatch.setattr("dotfiles.cmd.brew.service.mkdtemp", lambda *, prefix: str(install_dir))
    installer = install_dir / "install.sh"
    runner.script(("curl", "-fsSL", "-o", str(installer), _CLAUDE_CODE_URL), exit_code=1)
    results = install_claude_code(runner)
    assert results[0].level == "error"


# ---------------------------------------------------------------------------
# install_typewhisper
# ---------------------------------------------------------------------------

# The fetch-URL shell command is imported from the service so
# tests script exactly the same tuple the implementation passes to runner.run().
_TW_FETCH_CMD = _TW_FETCH_URL  # tuple[str, str, str] — (sh, -c, <shell>)


def test_install_typewhisper_skips_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch Path.exists so /Applications/TypeWhisper.app looks present. With no
    # typewhisper.sh under dotfiles_dir=tmp_path, the config-apply step is a no-op.
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/Applications/TypeWhisper.app")
    runner = FakeProcessRunner()
    results = install_typewhisper(runner, dotfiles_dir=tmp_path)
    assert results[0].level == "info"
    assert "already installed" in results[0].message
    assert runner.calls == []


def test_install_typewhisper_no_url_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    runner = FakeProcessRunner()
    runner.script(_TW_FETCH_CMD, stdout="")
    results = install_typewhisper(runner, dotfiles_dir=tmp_path)
    assert results[0].level == "error"
    assert "no stable DMG" in results[0].message


def test_install_typewhisper_full_happy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    install_dir = tmp_path / "private-install"
    install_dir.mkdir(mode=0o700)
    monkeypatch.setattr(
        "dotfiles.cmd.brew.service.mkdtemp",
        lambda *, prefix: str(install_dir),
    )
    runner = FakeProcessRunner()
    tw_url = "https://github.com/TypeWhisper/typewhisper-mac/releases/download/v1.0/TypeWhisper.dmg"
    runner.script(_TW_FETCH_CMD, stdout=tw_url + "\n")
    dmg_path = str(install_dir / "TypeWhisper.dmg")
    runner.script(
        ("curl", "-fsSL", "-o", dmg_path, tw_url),
        exit_code=0,
    )
    _mount_cmd = (
        f"hdiutil attach {dmg_path!r} -nobrowse -noautoopen 2>/dev/null"
        " | grep -oE '/Volumes/.*' | tail -1"
    )
    runner.script(
        ("sh", "-c", _mount_cmd),
        stdout="/Volumes/TypeWhisper\n",
    )
    app_path = "/Volumes/TypeWhisper/TypeWhisper.app"
    runner.script(("codesign", "--verify", "--deep", "--strict", app_path))
    runner.script(
        ("codesign", "-dv", "--verbose=4", app_path),
        stderr="TeamIdentifier=2D8ALY3LCL\n",
    )
    runner.script(
        ("cp", "-R", app_path, "/Applications/"),
        exit_code=0,
    )
    results = install_typewhisper(runner, dotfiles_dir=tmp_path)
    assert results[0].level == "success"
    assert "TypeWhisper installed" in results[0].message
    assert ("curl", "-fsSL", "-o", dmg_path, tw_url) in runner.calls
    assert not install_dir.is_dir()


def test_install_typewhisper_rejects_wrong_signing_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    install_dir = tmp_path / "private-install"
    install_dir.mkdir(mode=0o700)
    monkeypatch.setattr("dotfiles.cmd.brew.service.mkdtemp", lambda *, prefix: str(install_dir))
    runner = FakeProcessRunner()
    url = "https://example.test/TypeWhisper.dmg"
    runner.script(_TW_FETCH_CMD, stdout=url)
    dmg_path = str(install_dir / "TypeWhisper.dmg")
    mount = (
        f"hdiutil attach {dmg_path!r} -nobrowse -noautoopen 2>/dev/null "
        "| grep -oE '/Volumes/.*' | tail -1"
    )
    runner.script(("sh", "-c", mount), stdout="/Volumes/TypeWhisper\n")
    app_path = "/Volumes/TypeWhisper/TypeWhisper.app"
    runner.script(("codesign", "-dv", "--verbose=4", app_path), stderr="TeamIdentifier=EVIL\n")

    results = install_typewhisper(runner, dotfiles_dir=tmp_path)

    assert results[0].level == "error"
    assert not any(call[0] == "cp" for call in runner.calls)


def test_install_typewhisper_applies_tracked_config_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # App already installed → no download, but tracked config is re-applied.
    script = tmp_path / "macos" / "typewhisper.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/Applications/TypeWhisper.app")
    runner = FakeProcessRunner()
    runner.script((str(script), "apply"), exit_code=0)
    results = install_typewhisper(runner, dotfiles_dir=tmp_path)
    assert any(r.level == "success" and "config applied" in r.message for r in results)


def test_install_typewhisper_config_apply_failure_is_warn_not_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A non-zero apply (e.g. app running) must never fail the install.
    script = tmp_path / "macos" / "typewhisper.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/Applications/TypeWhisper.app")
    runner = FakeProcessRunner()
    runner.script((str(script), "apply"), exit_code=1)
    results = install_typewhisper(runner, dotfiles_dir=tmp_path)
    assert any(r.level == "warn" for r in results)
    assert not any(r.level == "error" for r in results)


# ---------------------------------------------------------------------------
# install_npm_globals
# ---------------------------------------------------------------------------


def test_install_npm_globals_skips_present(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    # Both wrangler and agent-browser are already installed
    runner.script(("npm", "list", "-g", "--depth=0", "wrangler@4.112.0"), stdout="wrangler\n")
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="/usr/local/bin/agent-browser\n")

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    npm_calls = [c for c in runner.calls if c[0] == "npm"]
    assert npm_calls == [("npm", "list", "-g", "--depth=0", "wrangler@4.112.0")]
    assert all(r.level == "info" for r in results)


def test_install_npm_globals_skips_disabled(tmp_path: Path) -> None:
    """A disabled npm package is never installed, even when missing + flag is on."""
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("npm", "list", "-g", "--depth=0", "wrangler@4.112.0"), exit_code=1)
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="", exit_code=1)

    install_npm_globals(manifest, runner, flags_on={"ai"})
    # pinchtab is disabled — it must not be probed or installed
    assert ("sh", "-c", "command -v pinchtab") not in runner.calls
    assert ("npm", "install", "-g", "pinchtab") not in runner.calls


def test_install_npm_globals_installs_missing(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("npm", "list", "-g", "--depth=0", "wrangler@4.112.0"), exit_code=1)
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="", exit_code=1)

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    assert ("npm", "install", "-g", "wrangler@4.112.0") in runner.calls
    assert ("npm", "install", "-g", "agent-browser") in runner.calls
    assert all(r.level == "success" for r in results)


def test_install_npm_globals_flag_gates_ai_packages(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("npm", "list", "-g", "--depth=0", "wrangler@4.112.0"), exit_code=1)

    # ai OFF → agent-browser should NOT be installed
    install_npm_globals(manifest, runner, flags_on=set())
    npm_calls = [c for c in runner.calls if c[0] == "npm"]
    installed_names = {c[-1] for c in npm_calls}
    assert "agent-browser" not in installed_names
    assert "wrangler@4.112.0" in installed_names


def test_install_npm_globals_error_on_failure(tmp_path: Path) -> None:
    manifest = load(tmp_path)
    runner = FakeProcessRunner()
    runner.script(("npm", "list", "-g", "--depth=0", "wrangler@4.112.0"), exit_code=1)
    runner.script(("sh", "-c", "command -v agent-browser"), stdout="", exit_code=1)
    runner.script(("npm", "install", "-g", "wrangler@4.112.0"), exit_code=1)

    results = install_npm_globals(manifest, runner, flags_on={"ai"})
    levels = [r.level for r in results]
    assert "error" in levels


def test_install_go_tools_uses_exact_version(tmp_path: Path) -> None:
    go_package = """
[[go_package]]
name = "gopls"
module = "golang.org/x/tools/gopls"
version = "v0.23.0"
"""
    manifest = load(tmp_path, INSTALL_TOML + go_package)
    runner = FakeProcessRunner()
    runner.script(("which", "gopls"), exit_code=1)

    results = install_go_tools(manifest, runner, dry_run=False)

    assert ("go", "install", "golang.org/x/tools/gopls@v0.23.0") in runner.calls
    assert results[0].level == "success"


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def test_upgrade_runs_update_upgrade_and_cleanup() -> None:
    runner = FakeProcessRunner()
    steps = upgrade(runner)
    assert ("brew", "update") in runner.calls
    assert ("brew", "upgrade") in runner.calls
    assert ("brew", "cleanup", "--prune=30") in runner.calls
    assert not any(s.level == "error" for s in steps)


def test_upgrade_reports_error_when_upgrade_fails() -> None:
    runner = FakeProcessRunner()
    runner.script(("brew", "upgrade"), exit_code=1, stderr="boom")
    steps = upgrade(runner)
    errors = [s for s in steps if s.level == "error"]
    assert len(errors) == 1
    assert "boom" in (errors[0].details or "")


def test_upgrade_stops_when_update_fails() -> None:
    runner = FakeProcessRunner()
    runner.script(("brew", "update"), exit_code=1, stderr="offline")
    steps = upgrade(runner)
    assert [step.level for step in steps] == ["error"]
    assert ("brew", "upgrade") not in runner.calls


def test_upgrade_reports_cleanup_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("brew", "cleanup", "--prune=30"), exit_code=1, stderr="busy")
    steps = upgrade(runner)
    assert any(step.level == "warn" and "cleanup" in step.message for step in steps)
