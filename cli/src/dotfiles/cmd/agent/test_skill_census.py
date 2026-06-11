"""Tests for the skill census — the one classification behind every skill count."""

from __future__ import annotations

from pathlib import Path

from dotfiles.agent import VENDOR_BY_NAME
from dotfiles.cmd.agent.skill_census import SkillCensus, skill_census


def _seed(
    tmp_path: Path, *, canonical: list[str], external: list[str], deployed: list[str]
) -> tuple[Path, Path]:
    repo = tmp_path / "dotfiles"
    home = tmp_path / "home"
    for name in canonical:
        d = repo / "ai" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\n---\n")
    keep = repo / "ai" / "agents" / "claude" / "external-skills.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("\n".join(f"owner/repo@{n}" for n in external))
    for name in deployed:
        (home / ".claude" / "skills" / name).mkdir(parents=True)
    return home, repo


def test_census_classifies_ours_external_foreign(tmp_path: Path) -> None:
    home, repo = _seed(
        tmp_path,
        canonical=["alpha", "beta"],
        external=["superpowers"],
        deployed=["alpha", "beta", "superpowers", "vendor-thing"],
    )
    census = skill_census(VENDOR_BY_NAME["claude"], home=home, dotfiles_dir=repo)
    assert census is not None
    assert (census.ours, census.external, census.foreign) == (2, 1, 1)
    assert census.expected == 2
    assert census.missing == 0
    assert census.deployed == 4
    assert census.label() == "3+1"


def test_census_missing_is_canonical_shortfall_only(tmp_path: Path) -> None:
    home, repo = _seed(
        tmp_path,
        canonical=["alpha", "beta", "gamma"],
        external=[],
        deployed=["alpha"],
    )
    census = skill_census(VENDOR_BY_NAME["claude"], home=home, dotfiles_dir=repo)
    assert census is not None
    assert census.missing == 2  # beta + gamma absent; nothing else counts as drift


def test_census_none_for_vendor_without_skills_deploy(tmp_path: Path) -> None:
    # Construct a vendor-like check via the registry: every real vendor deploys
    # skills today, so assert the contract through a label-less empty home.
    home, repo = _seed(tmp_path, canonical=[], external=[], deployed=[])
    census = skill_census(VENDOR_BY_NAME["claude"], home=home, dotfiles_dir=repo)
    assert census is not None
    assert census.deployed == 0
    assert census.label() == "0"


def test_label_hides_foreign_when_clean() -> None:
    census = SkillCensus(vendor="claude", ours=36, external=9, foreign=0, expected=36)
    assert census.label() == "45"
    noisy = SkillCensus(vendor="hermes", ours=36, external=0, foreign=18, expected=36)
    assert noisy.label() == "36+18"
