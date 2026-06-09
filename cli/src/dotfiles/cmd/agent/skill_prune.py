"""Prune deployed skill dirs that are no longer canonical (deploy = mirror, not append).

`deploy_skills` removes our skills *by current name* before re-adding, so a renamed
or removed skill strands its old deployed copy forever. This reconciles that drift.

A deployed skill dir is a **retired** (safe-to-delete) orphan iff it was once one of
our canonical skills — proven by a ``*skills/<name>/SKILL.md`` path in this repo's git
history — yet is neither currently canonical nor tracked in external-skills.txt.
Anything never in the repo is **untracked** (an externally-installed skill); it's
reported but never auto-deleted, so a manual `npx skills add` is safe.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.result import StepResult

# Deployed skill directories we mirror, relative to $HOME. Codex + Pi share
# ~/.agents/skills; Cursor keeps its own (curated) set.
_SKILL_DIRS: tuple[tuple[str, ...], ...] = (
    (".claude", "skills"),
    (".agents", "skills"),
    (".codex", "skills"),
    (".cursor", "skills"),
    (".cursor", "skills-cursor"),
)

# Matches any historical skills path: `.ai/skills/<name>/SKILL.md`, `ai/skills/...`, etc.
_HISTORY_RE = re.compile(r"(?:^|/)skills/([^/]+)/SKILL\.md$")


class SkillOrphan(BaseModel):
    """A deployed skill dir not in the current canonical/external keep-set."""

    model_config = ConfigDict(frozen=True)

    location: str  # e.g. ".agents/skills"
    name: str
    path: str
    retired: bool  # True = was ours (safe to prune); False = untracked external


def canonical_skill_names(dotfiles_dir: Path) -> set[str]:
    """Names of the current canonical skills (ai/skills/*/SKILL.md)."""
    root = dotfiles_dir / "ai" / "skills"
    if not root.is_dir():
        return set()
    return {p.parent.name for p in root.glob("*/SKILL.md")}


def external_skill_names(dotfiles_dir: Path) -> set[str]:
    """Intentional third-party skills tracked in external-skills.txt (owner/repo@skill)."""
    keep_file = dotfiles_dir / "ai" / "agents" / "claude" / "external-skills.txt"
    names: set[str] = set()
    if not keep_file.is_file():
        return names
    for raw in keep_file.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()  # drop inline comments
        if not line:
            continue
        # `owner/repo@skill` → the skill name follows the last '@' (else the path tail)
        tail = line.rsplit("@", 1)[-1] if "@" in line else line.rsplit("/", 1)[-1]
        if tail := tail.strip():
            names.add(tail)
    return names


def ever_ours_names(runner: ProcessRunner, dotfiles_dir: Path) -> set[str]:
    """Skill names that ever existed as a canonical SKILL.md in this repo's git history.

    Git is the provenance record: if absent, we can't prove the skill was ours, so
    we treat it as untracked and leave it alone.
    """
    result = runner.run(
        ("git", "-C", str(dotfiles_dir), "log", "--all", "--pretty=format:", "--name-only")
    )
    if not result.ok:
        return set()
    return {
        m.group(1) for line in result.stdout.splitlines() if (m := _HISTORY_RE.search(line.strip()))
    }


def find_orphans(runner: ProcessRunner, home: Path, dotfiles_dir: Path) -> list[SkillOrphan]:
    """Deployed skill dirs not in the canonical/external keep-set, classified by provenance."""
    keep = canonical_skill_names(dotfiles_dir) | external_skill_names(dotfiles_dir)
    ours = ever_ours_names(runner, dotfiles_dir)
    orphans: list[SkillOrphan] = []
    for parts in _SKILL_DIRS:
        target = home.joinpath(*parts)
        if not target.is_dir():
            continue
        location = "/".join(parts)
        for sub in sorted(target.iterdir(), key=lambda p: p.name):
            if not sub.is_dir() or sub.name in keep:
                continue
            orphans.append(
                SkillOrphan(
                    location=location, name=sub.name, path=str(sub), retired=sub.name in ours
                )
            )
    return orphans


def prune_orphans(orphans: list[SkillOrphan], *, dry_run: bool) -> list[StepResult]:
    """Delete the retired orphans (untracked ones are never touched). dry_run reports only."""
    steps: list[StepResult] = []
    for orphan in (o for o in orphans if o.retired):
        target = f"{orphan.location}/{orphan.name}"
        if dry_run:
            steps.append(StepResult(level="info", message=f"DRY RUN: rm {target}"))
        else:
            shutil.rmtree(orphan.path, ignore_errors=True)
            steps.append(StepResult(level="success", message=f"Removed {target}"))
    return steps
