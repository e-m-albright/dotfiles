"""Tests for `dotfiles verify vendors` Typer command."""

from pathlib import Path

from typer.testing import CliRunner

from dotfiles_cli.cli.main import app
from tests.fakes import FakeFileSystem, make_fake_context

runner = CliRunner()


def test_verify_vendors_exits_zero() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_verify_vendors_prints_claude_code_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "Claude Code" in result.output


def test_verify_vendors_prints_cursor_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "Cursor" in result.output


def test_verify_vendors_prints_codex_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "Codex" in result.output


def test_verify_vendors_prints_gemini_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "Gemini" in result.output


def test_verify_vendors_prints_pi_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "Pi" in result.output


def test_verify_vendors_missing_paths_show_red_glyph() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    # bare fake context → all paths missing → ✗ glyphs
    assert "✗" in result.output


def test_verify_vendors_present_path_shows_check_glyph() -> None:
    fs = FakeFileSystem()
    h = Path("/home/evan")
    fs.write_text(h / ".claude.json", "{}")
    ctx = make_fake_context(fs=fs, home=h)
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "✓" in result.output


def test_verify_vendors_empty_dir_shows_circle_glyph() -> None:
    fs = FakeFileSystem()
    h = Path("/home/evan")
    fs.mkdir(h / ".claude" / "skills")
    ctx = make_fake_context(fs=fs, home=h)
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "○" in result.output


def test_verify_vendors_prints_static_summary_lines() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "npx skills" in result.output
    assert "dotfiles agent setup" in result.output


def test_verify_vendors_prints_cli_confirmation_lines() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    assert "CLI confirmation" in result.output


def test_verify_vendors_gemini_skipped_when_absent() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["verify", "vendors"], obj=ctx)
    # gemini not in PATH in fake context → skipped line
    assert "skipped" in result.output or "-" in result.output


def test_verify_vendors_help_is_available() -> None:
    result = runner.invoke(app, ["verify", "vendors", "--help"])
    assert result.exit_code == 0
