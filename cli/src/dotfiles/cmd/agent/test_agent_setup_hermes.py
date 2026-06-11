"""Tests for cmd/agent/vendors/hermes.py.

All tests use tmp_path for home + dotfiles_dir; no real home is touched. Hermes is
a skills-only vendor: setup symlinks the canonical ai/skills into ~/.hermes/skills.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.cmd.agent.vendors.hermes import setup_hermes
from dotfiles.testing.fakes import FakeProcessRunner, write_tree


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "ai/skills/alpha/SKILL.md": "# Alpha",
            "ai/skills/beta/SKILL.md": "# Beta",
        },
    )
    return d


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


def _which_present(name: str) -> str | None:
    return "/Users/x/.local/bin/hermes" if name == "hermes" else None


def _which_absent(_name: str) -> str | None:
    return None


def test_skips_when_hermes_not_installed(dotfiles: Path, home: Path) -> None:
    results = setup_hermes(
        runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_absent
    )
    assert len(results) == 1
    assert "skipped" in results[0].message
    assert results[0].ok
    # Nothing is created when hermes is absent.
    assert not (home / ".hermes").exists()


def test_symlinks_canonical_skills(dotfiles: Path, home: Path) -> None:
    results = setup_hermes(
        runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_present
    )
    skills = home / ".hermes" / "skills"
    assert (skills / "alpha").is_symlink()
    assert (skills / "beta").is_symlink()
    assert (skills / "alpha").resolve() == (dotfiles / "ai" / "skills" / "alpha").resolve()
    assert any("2 skills" in r.message for r in results)


def test_replaces_stale_copied_dir_with_symlink(dotfiles: Path, home: Path) -> None:
    """A prior `npx skills --copy` leaves a real dir; setup must replace it with a link."""
    stale = home / ".hermes" / "skills" / "alpha"
    write_tree(home / ".hermes" / "skills", {"alpha/SKILL.md": "# stale copy"})
    assert stale.is_dir()
    assert not stale.is_symlink()

    setup_hermes(runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_present)
    assert stale.is_symlink()
    assert stale.resolve() == (dotfiles / "ai" / "skills" / "alpha").resolve()


def test_leaves_external_skills_untouched(dotfiles: Path, home: Path) -> None:
    """A skill we don't own (no canonical match) must survive the deploy."""
    external = home / ".hermes" / "skills" / "superpowers"
    write_tree(home / ".hermes" / "skills", {"superpowers/SKILL.md": "# external"})

    setup_hermes(runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_present)
    assert external.is_dir()
    assert not external.is_symlink()
    assert (external / "SKILL.md").read_text() == "# external"


def test_is_idempotent(dotfiles: Path, home: Path) -> None:
    for _ in range(2):
        results = setup_hermes(
            runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_present
        )
        assert all(r.ok for r in results)
    skills = home / ".hermes" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["alpha", "beta"]
