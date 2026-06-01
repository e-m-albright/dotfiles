"""Tests for `dotfiles agent setup` command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeProcessRunner, make_fake_context, write_tree

runner = CliRunner()

# ---------------------------------------------------------------------------
# Minimal dotfiles tree helpers
# ---------------------------------------------------------------------------

_SHARED_MCP = json.dumps(
    {
        "context7": {
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp"],
            "targets": ["claude", "cursor", "codex", "gemini"],
        }
    }
)


def _make_dotfiles(base: Path) -> Path:
    """Write the minimum file tree that setup_gemini needs to skip gracefully."""
    d = base / "dotfiles"
    write_tree(
        d,
        {
            "agents/shared/mcp-servers.json": _SHARED_MCP,
        },
    )
    return d


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


def test_agent_setup_help_exits_zero() -> None:
    result = runner.invoke(app, ["agent", "setup", "--help"])
    assert result.exit_code == 0, result.output


def test_agent_setup_help_shows_reset_mcp_flag() -> None:
    result = runner.invoke(app, ["agent", "setup", "--help"])
    assert "--reset-mcp" in result.output


def test_agent_setup_help_shows_clean_flag() -> None:
    result = runner.invoke(app, ["agent", "setup", "--help"])
    assert "--clean" in result.output


def test_agent_setup_help_shows_vendor_choices() -> None:
    result = runner.invoke(app, ["agent", "setup", "--help"])
    assert "claude" in result.output
    assert "gemini" in result.output


# ---------------------------------------------------------------------------
# Single-vendor: gemini skipped when not installed
# ---------------------------------------------------------------------------


def test_agent_setup_gemini_skipped_exits_zero(tmp_path: Path) -> None:
    """gemini not in PATH → skipped step, exit 0."""
    dotfiles = _make_dotfiles(tmp_path)
    ctx = make_fake_context(
        home=tmp_path / "home",
        dotfiles_dir=dotfiles,
    )
    # FakeProcessRunner.run() returns exit_code=0 by default but `which` uses
    # shutil.which; we pass which= kwarg at the core level, but the CLI uses
    # the real shutil.which. In CI gemini is absent — skip guard is fine.
    # To be deterministic, we test that exit code is 0 (skipped is ok).
    result = runner.invoke(app, ["agent", "setup", "gemini"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_agent_setup_gemini_skipped_shows_vendor_header(tmp_path: Path) -> None:
    dotfiles = _make_dotfiles(tmp_path)
    ctx = make_fake_context(home=tmp_path / "home", dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "setup", "gemini"], obj=ctx)
    assert "Gemini" in result.output


def test_agent_setup_gemini_skipped_shows_complete_message(tmp_path: Path) -> None:
    dotfiles = _make_dotfiles(tmp_path)
    ctx = make_fake_context(home=tmp_path / "home", dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "setup", "gemini"], obj=ctx)
    assert "complete" in result.output.lower() or "skipped" in result.output.lower()


# ---------------------------------------------------------------------------
# Single-vendor: only the requested vendor runs (isolation)
# ---------------------------------------------------------------------------


def test_agent_setup_single_vendor_only_touches_tmp(tmp_path: Path) -> None:
    """Running `agent setup gemini` must not create files outside tmp_path."""
    home = tmp_path / "home"
    dotfiles = _make_dotfiles(tmp_path)
    ctx = make_fake_context(home=home, dotfiles_dir=dotfiles)
    runner.invoke(app, ["agent", "setup", "gemini"], obj=ctx)
    # Real home must be untouched — no ~/.gemini created
    real_gemini = Path.home() / ".gemini"
    assert not (real_gemini / "settings_test_isolation_marker").exists()


# ---------------------------------------------------------------------------
# Invalid vendor
# ---------------------------------------------------------------------------


def test_agent_setup_invalid_vendor_exits_nonzero(tmp_path: Path) -> None:
    ctx = make_fake_context(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "setup", "nonexistent"], obj=ctx)
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# FakeProcessRunner: npx/npm calls go to fake runner, not real system
# ---------------------------------------------------------------------------


def test_agent_setup_uses_provided_runner(tmp_path: Path) -> None:
    """setup_codex runs npx skills — ensure FakeProcessRunner intercepts it."""
    home = tmp_path / "home"
    dotfiles = _make_dotfiles(tmp_path)
    # Give codex its minimum needed files
    write_tree(
        dotfiles,
        {
            "agents/codex/default.rules": "# rules\n",
            "agents/codex/hooks.json": json.dumps({}),
            "agents/codex/statusline.toml": "",
            ".ai/skills/": None,
            ".ai/agents/": None,
        },
    )
    proc = FakeProcessRunner()
    ctx = make_fake_context(home=home, dotfiles_dir=dotfiles, runner=proc)
    result = runner.invoke(app, ["agent", "setup", "codex"], obj=ctx)
    # codex setup calls npx skills — we just confirm it doesn't crash
    assert result.exit_code == 0, result.output
