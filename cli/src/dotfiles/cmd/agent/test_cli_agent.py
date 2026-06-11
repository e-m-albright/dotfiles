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
    skills_root = dotfiles / "ai" / "skills"
    skill_dir = skills_root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(_VALID_SKILL_TEXT)
    return dotfiles


def _dotfiles_with_invalid_skill(base: Path) -> Path:
    dotfiles = base / "dotfiles"
    skills_root = dotfiles / "ai" / "skills"
    skill_dir = skills_root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# no frontmatter\n")
    return dotfiles


def _dotfiles_with_chunks(base: Path, *chunks: tuple[str, str]) -> Path:
    dotfiles = base / "dotfiles"
    chunks_dir = dotfiles / "ai" / "prompts" / "gemini-chunks"
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
    assert "MCP servers" in result.output


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
# agent skills (list) — builtin hiding
# ---------------------------------------------------------------------------


def _home_with_vendor_builtin(base: Path, name: str = "vendor-thing") -> Path:
    """A fake $HOME with one Cursor-shipped builtin skill (only in skills-cursor)."""
    home = base / "home"
    skill = home / ".cursor" / "skills-cursor" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Use when the vendor ships this natively.\n---\n\n# X\n"
    )
    return home


def test_agent_skills_hides_builtin_by_default(tmp_path: Path) -> None:
    home = _home_with_vendor_builtin(tmp_path)
    ctx = make_fake_context(home=home, dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "skills"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "vendor-thing" not in result.output
    assert "1 vendor builtin hidden" in result.output


def test_agent_skills_all_shows_builtin(tmp_path: Path) -> None:
    home = _home_with_vendor_builtin(tmp_path)
    ctx = make_fake_context(home=home, dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "skills", "--all"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "vendor-thing" in result.output
    assert "builtin" in result.output


# ---------------------------------------------------------------------------
# agent web copy
# ---------------------------------------------------------------------------


def test_gemini_prompt_list_exits_zero(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"), ("02-b.md", "world!"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_gemini_prompt_list_prints_chunk_names(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"), ("02-b.md", "world!"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert "01-a.md" in result.output
    assert "02-b.md" in result.output


def test_gemini_prompt_list_prints_char_counts(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"))
    ctx = make_fake_context(dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert "5" in result.output  # len("hello".encode()) == 5


def test_gemini_prompt_default_missing_pbcopy_exits_one(tmp_path: Path) -> None:
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "hello"))
    proc = FakeProcessRunner()
    ctx = make_fake_context(runner=proc, dotfiles_dir=dotfiles)
    list_result = runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert list_result.exit_code == 0


def test_gemini_prompt_list_no_pbcopy_required(tmp_path: Path) -> None:
    """--list must not call pbcopy at all."""
    dotfiles = _dotfiles_with_chunks(tmp_path, ("01-a.md", "abc"))
    proc = FakeProcessRunner()
    ctx = make_fake_context(runner=proc, dotfiles_dir=dotfiles)
    runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert ("pbcopy",) not in proc.calls


def test_gemini_prompt_missing_chunks_dir_exits_one(tmp_path: Path) -> None:
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "web", "copy", "--list"], obj=ctx)
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Bracket safety: Rich markup must not eat "[...]" in dynamic content
# ---------------------------------------------------------------------------


def test_agent_overview_bracket_in_mcp_server_name_survives(tmp_path: Path) -> None:
    """MCP server name containing brackets must appear verbatim in output."""
    home = tmp_path / "home"
    claude_cfg = home / ".claude.json"
    claude_cfg.parent.mkdir(parents=True)
    claude_cfg.write_text(json.dumps({"mcpServers": {"srv[x]": {}}}))
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles", home=home)
    result = runner.invoke(app, ["agent", "overview"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "srv[x]" in result.output


# ---------------------------------------------------------------------------
# agent health — code-health backbone bootstrap
# ---------------------------------------------------------------------------

_HEALTH_CARD = json.dumps(
    {
        "loc": 4242,
        "since": "6 months ago",
        "suppressions": {"type-ignore": 2},
        "hotspots": [{"file": "cli/src/big.py", "score": 900, "churn": 30, "loc": 30}],
    }
)


def _health_ctx(tmp_path: Path):
    """A context whose runner scripts git-root + scorecard so `agent health` runs offline."""
    dotfiles = tmp_path / "dotfiles"
    target = tmp_path / "target"
    target.mkdir()
    scripts = dotfiles / "ai" / "skills" / "converge" / "scripts"
    proc = FakeProcessRunner()
    proc.script(("git", "rev-parse", "--show-toplevel"), stdout=str(target) + "\n")
    proc.script((str(scripts / "scorecard.sh"), "--json"), stdout=_HEALTH_CARD)
    return make_fake_context(runner=proc, dotfiles_dir=dotfiles), target


def test_agent_health_bootstraps_backbone(tmp_path: Path) -> None:
    ctx, target = _health_ctx(tmp_path)
    result = runner.invoke(app, ["agent", "health", "--scope", "demo"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "Code-health backbone" in result.output
    assert (target / "docs" / "health" / "demo" / "baselines.json").exists()
    assert (target / "docs" / "health" / "demo" / "findings.md").exists()


def test_agent_health_outside_repo_exits_one(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    proc = FakeProcessRunner()
    proc.script(("git", "rev-parse", "--show-toplevel"), exit_code=128)
    ctx = make_fake_context(runner=proc, dotfiles_dir=dotfiles)
    result = runner.invoke(app, ["agent", "health"], obj=ctx)
    assert result.exit_code == 1
    assert "not inside a git repo" in result.output


def test_agent_catechism_is_subsumed_into_instructions(tmp_path: Path) -> None:
    # `catechism` now delegates to the instructions tree, with the doctrine backbone
    # and the symptom→rite routing folded in (scope-health moved to the baselines).
    ctx = make_fake_context(dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["agent", "catechism"], obj=ctx)
    assert result.exit_code == 0, result.output
    for fragment in ("part of", "doctrine", "Canon", "routing"):
        assert fragment in result.output
    for rite in ("code-health", "form-prune", "systematic-debugging"):
        assert rite in result.output


def test_order_by_origin_groups_by_origin_then_name() -> None:
    """`agent skills` lists by origin (canonical → … → untracked) then name within."""
    from dotfiles.cmd.agent.render.skills import order_by_origin
    from dotfiles.cmd.agent.skill_inventory import SkillInfo

    def s(name: str, origin: str) -> SkillInfo:
        return SkillInfo(name=name, origin=origin, description="", source="")  # type: ignore[arg-type]

    # Deliberately shuffled across origins and names.
    skills = [
        s("zulu", "canonical"),
        s("beta", "untracked"),
        s("alpha", "canonical"),
        s("mike", "plugin"),
        s("alpha", "untracked"),
        s("delta", "external"),
    ]
    ordered = [(x.origin, x.name) for x in order_by_origin(skills)]
    assert ordered == [
        ("canonical", "alpha"),
        ("canonical", "zulu"),
        ("external", "delta"),
        ("plugin", "mike"),
        ("untracked", "alpha"),
        ("untracked", "beta"),
    ]


def test_origin_provenance_surfaces_plugin_marketplace_ref() -> None:
    """A plugin section header names its marketplace ref(s) — the real provenance —
    and de-dupes/sorts them; other origins use a static management hint."""
    from dotfiles.cmd.agent.render.skills import origin_provenance
    from dotfiles.cmd.agent.skill_inventory import SkillInfo

    def s(name: str, origin: str, source: str) -> SkillInfo:
        return SkillInfo(name=name, origin=origin, description="", source=source)  # type: ignore[arg-type]

    superpowers = [
        s("brainstorming", "plugin", "superpowers@claude-plugins-official"),
        s("writing-plans", "plugin", "superpowers@claude-plugins-official"),
    ]
    assert origin_provenance("plugin", superpowers) == (
        "superpowers@claude-plugins-official — manage via /plugin"
    )

    multi = [s("a", "plugin", "zeta@m"), s("b", "plugin", "alpha@m")]
    assert origin_provenance("plugin", multi) == "alpha@m, zeta@m — manage via /plugin"

    canonical = [s("converge", "canonical", "ai/skills/converge")]
    assert origin_provenance("canonical", canonical) == "this repo, ai/skills/ — edit directly"
