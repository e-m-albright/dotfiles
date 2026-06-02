"""Tests for `dotfiles agent` Typer commands (overview + lint + gemini-prompt)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()

_VALID_SKILL_TEXT = (
    "---\n"
    "name: my-skill\n"
    "description: Use when you need to do something useful here.\n"
    "---\n\n"
    "# My Skill\n\nDoes things.\n"
)


def _dotfiles_with_valid_skill(base: Path) -> Path:
    dotfiles = base / "dotfiles"
    skills_root = dotfiles / ".ai" / "skills"
    skill_dir = skills_root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(_VALID_SKILL_TEXT)
    return dotfiles


def _dotfiles_with_invalid_skill(base: Path) -> Path:
    dotfiles = base / "dotfiles"
    skills_root = dotfiles / ".ai" / "skills"
    skill_dir = skills_root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# no frontmatter\n")
    return dotfiles


def _dotfiles_with_chunks(base: Path, *chunks: tuple[str, str]) -> Path:
    dotfiles = base / "dotfiles"
    chunks_dir = dotfiles / "prompts" / "gemini-chunks"
    chunks_dir.mkdir(parents=True)
    for name, content in chunks:
        (chunks_dir / name).write_text(content)
    return dotfiles


# ---------------------------------------------------------------------------
# agent overview
# ---------------------------------------------------------------------------


def test_agent_overview_exits_zero(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_agent_overview_prints_mcp_servers_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "MCP Servers" in result.output


def test_agent_overview_prints_skills_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Skills" in result.output


def test_agent_overview_prints_subagents_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Subagents" in result.output


def test_agent_overview_prints_hooks_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Hooks" in result.output


def test_agent_overview_prints_rules_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert "Rules" in result.output


def test_agent_overview_prints_permissions_header(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
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


def test_agent_lint_valid_skill_exits_zero(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_valid_skill(tmp_path)
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_agent_lint_valid_skill_shows_ok(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_valid_skill(tmp_path)
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "OK" in result.output


def test_agent_lint_invalid_skill_exits_one(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_invalid_skill(tmp_path)
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 1


def test_agent_lint_invalid_skill_shows_fail(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_invalid_skill(tmp_path)
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "FAIL" in result.output


def test_agent_lint_shows_summary(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_valid_skill(tmp_path)
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert "Summary" in result.output
    assert "passed" in result.output


def test_agent_lint_empty_dotfiles_exits_zero(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "lint"], obj=ctx)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# agent web-chat-instructions
# ---------------------------------------------------------------------------


def test_gemini_prompt_list_exits_zero(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"), ("02-b.md", "world!"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_gemini_prompt_list_prints_chunk_names(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"), ("02-b.md", "world!"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert "01-a.md" in result.output
    assert "02-b.md" in result.output


def test_gemini_prompt_list_prints_char_counts(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert "5" in result.output  # len("hello".encode()) == 5


def test_gemini_prompt_default_missing_pbcopy_exits_one(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"))
    proc = FakeProcessRunner()
    ctx = make_fake_context(runner=proc, dotfiles_dir=dotfiles)
    list_result = runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert list_result.exit_code == 0


def test_gemini_prompt_list_no_pbcopy_required(tmp_path: Path) -> None:
    """--list must not call pbcopy at all."""
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "abc"))
    proc = FakeProcessRunner()
    ctx = make_fake_context(runner=proc, dotfiles_dir=dotfiles)
    runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert ("pbcopy",) not in proc.calls


def test_gemini_prompt_missing_chunks_dir_exits_one(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "web-chat-instructions", "--list"], obj=ctx)
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Bracket safety: Rich markup must not eat "[...]" in dynamic content
# ---------------------------------------------------------------------------


def test_agent_overview_bracket_in_mcp_server_name_survives(tmp_path: Path) -> None:
    """MCP server name containing brackets must appear verbatim in output."""
    dotfiles = tmp_path / "dotfiles"
    mcp_path = dotfiles / "agents" / "shared" / "mcp-servers.json"
    mcp_path.parent.mkdir(parents=True)
    mcp_path.write_text(
        json.dumps({"srv[x]": {"command": "npx", "args": [], "targets": ["claude"]}})
    )
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "srv[x]" in result.output
