from pathlib import Path

from dotfiles.cmd.agent.skill_collision import (
    collision_report,
    local_skill_surfaces,
    pi_package_skill_surfaces,
)
from dotfiles.testing.fakes import write_tree


def _skill_md(name: str, desc: str) -> str:
    return f"---\nname: {name}\ndescription: {desc}\n---\n\nbody\n"


def test_local_skill_surfaces_reads_canonical_skills(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    write_tree(
        dotfiles,
        {
            "ai/skills/review/SKILL.md": _skill_md("review", "Review a PR or diff"),
            "ai/skills/diagnose/SKILL.md": _skill_md("diagnose", "Debug a failing test"),
        },
    )

    skills = local_skill_surfaces(dotfiles)

    assert [(s.name, s.source_kind) for s in skills] == [
        ("diagnose", "canonical"),
        ("review", "canonical"),
    ]
    assert skills[0].path == "ai/skills/diagnose/SKILL.md"


def test_pi_package_skill_surfaces_reads_installed_pi_packages(tmp_path: Path) -> None:
    home = tmp_path / "home"
    write_tree(
        home,
        {
            ".pi/agent/npm/node_modules/some-pack/package.json": """
            {
              "name": "some-pack",
              "pi": { "skills": ["skills"] }
            }
            """,
            ".pi/agent/npm/node_modules/some-pack/skills/testing/SKILL.md": _skill_md(
                "testing", "Test-driven development workflow"
            ),
            ".pi/agent/npm/node_modules/no-pi/skills/ignored/SKILL.md": _skill_md(
                "ignored", "Ignored"
            ),
        },
    )

    skills = pi_package_skill_surfaces(home)

    assert len(skills) == 1
    assert skills[0].name == "testing"
    assert skills[0].source_kind == "pi-package"
    assert skills[0].source == "some-pack"


def test_collision_report_flags_local_external_domain_overlap(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    home = tmp_path / "home"
    write_tree(
        dotfiles,
        {
            "ai/skills/tdd-vertical-slices/SKILL.md": _skill_md(
                "tdd-vertical-slices", "Vertical-slice red-green-refactor TDD for feature work"
            ),
            "ai/skills/review/SKILL.md": _skill_md(
                "review", "Pre-merge review of a diff, branch, or PR"
            ),
        },
    )
    write_tree(
        home,
        {
            ".pi/agent/npm/node_modules/super/package.json": """
            { "name": "super", "pi": { "skills": ["skills"] } }
            """,
            ".pi/agent/npm/node_modules/super/skills/test-driven-development/SKILL.md": _skill_md(
                "test-driven-development", "TDD red green refactor workflow"
            ),
            ".pi/agent/npm/node_modules/super/skills/native-web-search/SKILL.md": _skill_md(
                "native-web-search", "Search the web"
            ),
        },
    )

    report = collision_report(home=home, dotfiles_dir=dotfiles)

    assert [c.domain for c in report.collisions] == ["tdd"]
    assert report.collisions[0].local.name == "tdd-vertical-slices"
    assert report.collisions[0].external.name == "test-driven-development"


def test_collision_report_flags_exact_name_shadowing(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    home = tmp_path / "home"
    write_tree(dotfiles, {"ai/skills/github/SKILL.md": _skill_md("github", "GitHub workflow")})
    write_tree(
        home,
        {
            ".pi/agent/npm/node_modules/mitsupi/package.json": """
            { "name": "mitsupi", "pi": { "skills": ["skills"] } }
            """,
            ".pi/agent/npm/node_modules/mitsupi/skills/github/SKILL.md": _skill_md(
                "github", "GitHub CLI helper"
            ),
        },
    )

    report = collision_report(home=home, dotfiles_dir=dotfiles)

    assert len(report.collisions) == 1
    assert report.collisions[0].kind == "same-name"
    assert report.collisions[0].domain == "github"
