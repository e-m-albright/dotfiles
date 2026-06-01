"""Tests for `dotfiles agent` Typer commands (overview + lint)."""

from pathlib import Path

from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeFileSystem, make_fake_context

runner = CliRunner()

_DOTFILES = Path("/home/evan/dotfiles")
_SKILLS_ROOT = _DOTFILES / ".ai" / "skills"

_VALID_SKILL_TEXT = (
    "---\n"
    "name: my-skill\n"
    "description: Use when you need to do something useful here.\n"
    "---\n\n"
    "# My Skill\n\nDoes things.\n"
)


def _fs_with_valid_skill() -> FakeFileSystem:
    fs = FakeFileSystem()
    fs.mkdir(_SKILLS_ROOT)
    skill_dir = _SKILLS_ROOT / "my-skill"
    fs.mkdir(skill_dir)
    fs.write_text(skill_dir / "SKILL.md", _VALID_SKILL_TEXT)
    return fs


def _fs_with_invalid_skill() -> FakeFileSystem:
    fs = FakeFileSystem()
    fs.mkdir(_SKILLS_ROOT)
    skill_dir = _SKILLS_ROOT / "my-skill"
    fs.mkdir(skill_dir)
    fs.write_text(skill_dir / "SKILL.md", "# no frontmatter\n")
    return fs


# ---------------------------------------------------------------------------
# agent overview
# ---------------------------------------------------------------------------


def test_agent_overview_exits_zero() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_agent_overview_prints_mcp_servers_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "MCP Servers" in result.output


def test_agent_overview_prints_skills_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Skills" in result.output


def test_agent_overview_prints_subagents_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Subagents" in result.output


def test_agent_overview_prints_hooks_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Hooks" in result.output


def test_agent_overview_prints_rules_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Rules" in result.output


def test_agent_overview_prints_permissions_header() -> None:
    ctx = make_fake_context()
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Permissions" in result.output


def test_agent_overview_help_is_available() -> None:
    result = runner.invoke(app, ["agent", "overview", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# agent lint
# ---------------------------------------------------------------------------


def test_agent_lint_help_is_available() -> None:
    result = runner.invoke(app, ["agent", "lint", "--help"])
    assert result.exit_code == 0


def test_agent_lint_valid_skill_exits_zero() -> None:
    ctx = make_fake_context(fs=_fs_with_valid_skill(), dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_agent_lint_valid_skill_shows_ok() -> None:
    ctx = make_fake_context(fs=_fs_with_valid_skill(), dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "OK" in result.output


def test_agent_lint_invalid_skill_exits_one() -> None:
    ctx = make_fake_context(fs=_fs_with_invalid_skill(), dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 1


def test_agent_lint_invalid_skill_shows_fail() -> None:
    ctx = make_fake_context(fs=_fs_with_invalid_skill(), dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "FAIL" in result.output


def test_agent_lint_shows_summary() -> None:
    ctx = make_fake_context(fs=_fs_with_valid_skill(), dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "Summary" in result.output
    assert "passed" in result.output


def test_agent_lint_empty_dotfiles_exits_zero() -> None:
    ctx = make_fake_context(dotfiles_dir=_DOTFILES)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 0
