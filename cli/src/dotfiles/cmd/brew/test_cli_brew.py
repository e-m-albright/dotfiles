"""Tests for the `dotfiles brew` Typer commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()

# Minimal packages.toml for CLI tests
_PACKAGES_TOML = """\
[flags]
ai = true
productivity = true
social = true

[taps]
list = []

[[section]]
name = "Core"
kind = "formula"
packages = [
  { name = "git" },
]
"""


def _make_ctx(tmp_path: Path) -> object:
    """Build a fake context with packages.toml under tmp_path/macos/."""
    macos_dir = tmp_path / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    (macos_dir / "packages.toml").write_text(_PACKAGES_TOML)

    runner_fake = FakeProcessRunner()
    # brew list/leaves commands return empty (nothing installed)
    runner_fake.script(("brew", "list", "--formula", "-1"), stdout="")
    runner_fake.script(("brew", "leaves", "--installed-on-request"), stdout="")
    runner_fake.script(("brew", "list", "--cask", "-1"), stdout="")

    return make_fake_context(
        runner=runner_fake,
        home=tmp_path / "home",
        dotfiles_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# brew --help
# ---------------------------------------------------------------------------


def test_brew_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["brew", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "stale" in result.output
    assert "upgrade" in result.output


# ---------------------------------------------------------------------------
# brew upgrade
# ---------------------------------------------------------------------------


def test_brew_upgrade_runs_and_exits_zero(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "upgrade"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "Upgrading Homebrew packages" in result.output


def test_brew_upgrade_nonzero_exit_on_failure(tmp_path: Path) -> None:
    macos_dir = tmp_path / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    (macos_dir / "packages.toml").write_text(_PACKAGES_TOML)

    runner_fake = FakeProcessRunner()
    runner_fake.script(("brew", "upgrade"), exit_code=1, stderr="boom")
    ctx = make_fake_context(runner=runner_fake, home=tmp_path / "home", dotfiles_dir=tmp_path)
    result = runner.invoke(app, ["brew", "upgrade"], obj=ctx)
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# brew stale
# ---------------------------------------------------------------------------


def test_brew_stale_exit_zero(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "stale"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_brew_stale_shows_sections(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "stale"], obj=ctx)
    assert "Stale packages" in result.output
    assert "Missing packages" in result.output


def test_brew_stale_reports_missing(tmp_path: Path) -> None:
    """git is declared but not installed → appears in missing."""
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "stale"], obj=ctx)
    assert "git" in result.output


def test_brew_stale_reports_stale(tmp_path: Path) -> None:
    """Package installed but not declared → appears as stale."""
    macos_dir = tmp_path / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    (macos_dir / "packages.toml").write_text(_PACKAGES_TOML)

    runner_fake = FakeProcessRunner()
    runner_fake.script(("brew", "leaves", "--installed-on-request"), stdout="git\nextra-tool\n")
    runner_fake.script(("brew", "list", "--formula", "-1"), stdout="git\nextra-tool\n")
    runner_fake.script(("brew", "list", "--cask", "-1"), stdout="")

    ctx = make_fake_context(runner=runner_fake, home=tmp_path / "home", dotfiles_dir=tmp_path)
    result = runner.invoke(app, ["brew", "stale"], obj=ctx)
    assert "extra-tool" in result.output


# ---------------------------------------------------------------------------
# brew install --dry-run
# ---------------------------------------------------------------------------


def test_brew_install_dry_run_exit_zero(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "install", "--dry-run"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_brew_install_dry_run_no_mutating_runner_calls(tmp_path: Path) -> None:
    """--dry-run must not call brew install or rustup or npm install."""
    macos_dir = tmp_path / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    (macos_dir / "packages.toml").write_text(_PACKAGES_TOML)

    runner_fake = FakeProcessRunner()
    runner_fake.script(("brew", "list", "--formula", "-1"), stdout="")
    runner_fake.script(("brew", "list", "--cask", "-1"), stdout="")

    ctx = make_fake_context(runner=runner_fake, home=tmp_path / "home", dotfiles_dir=tmp_path)
    runner.invoke(app, ["brew", "install", "--dry-run"], obj=ctx)

    mutating = [
        c
        for c in runner_fake.calls
        if (c[0] == "brew" and "install" in c and "list" not in c)
        or (c[0] == "npm" and "install" in c)
        or any("rustup.rs" in part for part in c)
    ]
    assert mutating == [], f"Unexpected mutating calls in dry-run: {mutating}"


def test_brew_install_only_runs_specials_declared_by_manifest(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = runner.invoke(app, ["brew", "install"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert not any("rustup.rs" in part for call in ctx.runner.calls for part in call)


def test_manifest_flag_default_can_disable_a_section(tmp_path: Path) -> None:
    manifest = _PACKAGES_TOML.replace("ai = true", "ai = false").replace(
        'name = "Core"', 'name = "Core"\nflag = "ai"'
    )
    macos_dir = tmp_path / "macos"
    macos_dir.mkdir(parents=True)
    (macos_dir / "packages.toml").write_text(manifest)
    fake = FakeProcessRunner()
    fake.script(("brew", "list", "--formula", "-1"), stdout="")
    fake.script(("brew", "list", "--cask", "-1"), stdout="")
    ctx = make_fake_context(runner=fake, dotfiles_dir=tmp_path)

    result = runner.invoke(app, ["brew", "install", "--dry-run"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "brew install git" not in result.output
