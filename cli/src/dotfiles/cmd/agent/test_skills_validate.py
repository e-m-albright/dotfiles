"""Tests for SkillValidateService and validate_file (core/skills.py)."""

from pathlib import Path

from dotfiles.cmd.agent.skills import validate_file, validate_skill_files

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_VALID_SKILL = """\
---
name: my-skill
description: Use when you need to do something useful and important here.
---

# My Skill

This skill does things.
"""

_VALID_AGENT = """\
---
name: my-agent
description: Use when you need an agent for testing purposes in this repo.
---

# My Agent

Does agent things.
"""


def _skill_text(
    *,
    name: str = "my-skill",
    description: str = "Use when you need to do something useful and important here.",
    body: str = "# My Skill\n\nThis skill does things.\n",
) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# validate_file — unit tests (pure, no filesystem)
# ---------------------------------------------------------------------------


def test_valid_skill_is_ok() -> None:
    result = validate_file(
        _VALID_SKILL,
        kind="skill",
        expected_name="my-skill",
        rel_path=".ai/skills/my-skill/SKILL.md",
    )
    assert result.status == "ok"
    assert result.errors == ()
    assert result.warnings == ()
    assert result.body_lines > 0


def test_valid_agent_is_ok() -> None:
    result = validate_file(
        _VALID_AGENT, kind="agent", expected_name="my-agent", rel_path=".ai/agents/my-agent.md"
    )
    assert result.status == "ok"


def test_missing_frontmatter_is_fail() -> None:
    text = "# No frontmatter\n\nJust body text.\n"
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "fail"
    assert any("missing frontmatter" in e for e in result.errors)


def test_name_mismatch_is_fail() -> None:
    text = _skill_text(name="wrong-name")
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "fail"
    assert any("wrong-name" in e and "my-skill" in e for e in result.errors)


def test_bad_name_regex_is_fail() -> None:
    # Leading hyphen violates the pattern
    text = _skill_text(name="-bad-name")
    result = validate_file(
        text, kind="skill", expected_name="-bad-name", rel_path=".ai/skills/-bad-name/SKILL.md"
    )
    assert result.status == "fail"
    assert any("violates" in e for e in result.errors)


def test_bad_name_with_uppercase_is_fail() -> None:
    text = _skill_text(name="MySkill")
    result = validate_file(
        text, kind="skill", expected_name="MySkill", rel_path=".ai/skills/MySkill/SKILL.md"
    )
    assert result.status == "fail"
    assert any("violates" in e for e in result.errors)


def test_missing_description_is_fail() -> None:
    text = "---\nname: my-skill\n---\n\n# Body\n"
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "fail"
    assert any("missing description" in e for e in result.errors)


def test_long_body_is_warn() -> None:
    # 501 lines of body for a skill (limit=500)
    long_body = "\n".join(f"line {i}" for i in range(501))
    text = _skill_text(body=long_body)
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "warn"
    assert any("body" in w and "500" in w for w in result.warnings)


def test_agent_body_limit_is_200() -> None:
    long_body = "\n".join(f"line {i}" for i in range(201))
    text = _skill_text(body=long_body)
    result = validate_file(
        text, kind="agent", expected_name="my-skill", rel_path=".ai/agents/my-skill.md"
    )
    assert result.status == "warn"
    assert any("200" in w for w in result.warnings)


def test_no_trigger_clause_is_warn() -> None:
    text = _skill_text(description="A description without the magic words at all.")
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "warn"
    assert any("MISSING_TRIGGER" in w for w in result.warnings)


def test_trigger_when_also_accepted() -> None:
    text = _skill_text(description="Trigger when you see this pattern in the codebase.")
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    # No MISSING_TRIGGER warning
    assert not any("MISSING_TRIGGER" in w for w in result.warnings)


def test_too_many_caps_is_warn() -> None:
    # 16 occurrences of MUST → OVER_CONSTRAINED (threshold 15)
    body = " ".join(["MUST"] * 16) + "\n"
    text = _skill_text(body=body)
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "warn"
    assert any("OVER_CONSTRAINED" in w for w in result.warnings)


def test_exactly_15_caps_not_warned() -> None:
    body = " ".join(["MUST"] * 15) + "\n"
    text = _skill_text(body=body)
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert not any("OVER_CONSTRAINED" in w for w in result.warnings)


def test_caps_inside_identifier_not_counted() -> None:
    # MUSTACHE, ALWAYS_ON, NEVERMORE — none should count
    body = "MUSTACHE ALWAYS_ON NEVERMORE\n"
    text = _skill_text(body=body)
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert not any("OVER_CONSTRAINED" in w for w in result.warnings)


def test_short_description_is_warn() -> None:
    # Less than 20 chars, but has trigger clause
    text = _skill_text(description="Use when x.")  # 11 chars
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "warn"
    assert any("EMPTY_DESCRIPTION" in w for w in result.warnings)


def test_description_over_1024_is_fail() -> None:
    long_desc = "Use when " + "x" * 1020  # definitely > 1024
    text = _skill_text(description=long_desc)
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert result.status == "fail"
    assert any("1024" in e for e in result.errors)


def test_rel_path_and_kind_propagated() -> None:
    result = validate_file(
        _VALID_SKILL, kind="skill", expected_name="my-skill", rel_path="some/path/SKILL.md"
    )
    assert result.rel_path == "some/path/SKILL.md"
    assert result.kind == "skill"


# ---------------------------------------------------------------------------
# SkillValidateService — integration tests with real tmp_path
# ---------------------------------------------------------------------------


def _write_skill(dotfiles_dir: Path, name: str, text: str) -> None:
    skill_dir = dotfiles_dir / ".ai" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(text)


def _write_agent(dotfiles_dir: Path, name: str, text: str) -> None:
    agents_root = dotfiles_dir / ".ai" / "agents"
    agents_root.mkdir(parents=True, exist_ok=True)
    (agents_root / f"{name}.md").write_text(text)


def test_service_empty_dirs_returns_empty(tmp_path: Path) -> None:
    assert validate_skill_files(tmp_path) == []


def test_service_valid_skill_ok(tmp_path: Path) -> None:
    _write_skill(tmp_path, "my-skill", _skill_text())
    results = validate_skill_files(tmp_path)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].kind == "skill"


def test_service_missing_skill_md_is_fail(tmp_path: Path) -> None:
    # dir with no SKILL.md
    orphan = tmp_path / ".ai" / "skills" / "orphan-skill"
    orphan.mkdir(parents=True)
    results = validate_skill_files(tmp_path)
    assert len(results) == 1
    assert results[0].status == "fail"
    assert any("missing SKILL.md" in e for e in results[0].errors)


def test_service_valid_agent_ok(tmp_path: Path) -> None:
    _write_agent(tmp_path, "my-agent", _skill_text(name="my-agent"))
    results = validate_skill_files(tmp_path)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].kind == "agent"


def test_service_skills_and_agents_both_iterated(tmp_path: Path) -> None:
    _write_skill(tmp_path, "my-skill", _skill_text())
    _write_agent(tmp_path, "my-agent", _skill_text(name="my-agent"))
    results = validate_skill_files(tmp_path)
    assert len(results) == 2
    kinds = {r.kind for r in results}
    assert kinds == {"skill", "agent"}


def test_service_invalid_skill_propagated(tmp_path: Path) -> None:
    _write_skill(tmp_path, "my-skill", "# no frontmatter")
    results = validate_skill_files(tmp_path)
    assert results[0].status == "fail"


def test_service_agents_dir_absent_no_crash(tmp_path: Path) -> None:
    _write_skill(tmp_path, "my-skill", _skill_text())
    results = validate_skill_files(tmp_path)
    assert all(r.kind == "skill" for r in results)


# ---------------------------------------------------------------------------
# Fix 1 — trigger-clause regex must honor word boundaries
# ---------------------------------------------------------------------------


def test_use_whenever_does_not_satisfy_trigger() -> None:
    """'use whenever you like' must NOT count as a trigger clause (word boundary fix)."""
    text = _skill_text(description="use whenever you like to do something very useful indeed here.")
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert any("MISSING_TRIGGER" in w for w in result.warnings), (
        "Expected MISSING_TRIGGER warning for 'use whenever' but got: " + str(result.warnings)
    )


def test_use_when_x_satisfies_trigger() -> None:
    """'Use when X' must still suppress the MISSING_TRIGGER warning."""
    text = _skill_text(description="Use when you need to perform this specific action here.")
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert not any("MISSING_TRIGGER" in w for w in result.warnings), (
        "Unexpected MISSING_TRIGGER for valid 'Use when': " + str(result.warnings)
    )


# ---------------------------------------------------------------------------
# Fix 2 — unclosed frontmatter must produce empty body (no body-length warning)
# ---------------------------------------------------------------------------


def test_unclosed_frontmatter_no_body_length_warning() -> None:
    """A file with unclosed frontmatter and >500 total lines must NOT warn on body length."""
    fm_lines = "---\nname: my-skill\ndescription: Use when testing unclosed frontmatter here.\n"
    # 501 extra lines — would trigger body > 500 if mistakenly used as body
    extra = "\n".join(f"line {i}" for i in range(501))
    text = fm_lines + extra
    result = validate_file(
        text, kind="skill", expected_name="my-skill", rel_path=".ai/skills/my-skill/SKILL.md"
    )
    assert not any("body" in w and "500" in w for w in result.warnings), (
        "Spurious body-length warning for unclosed frontmatter: " + str(result.warnings)
    )
