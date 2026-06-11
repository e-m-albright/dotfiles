"""Prune deployed skill dirs that are no longer canonical (deploy = mirror, not append).

`deploy_skills` removes our skills *by current name* before re-adding, so a renamed
or removed skill strands its old deployed copy forever. This reconciles that drift.

A deployed skill not in the canonical/external keep-set is classified by source:

- **retired** — was once one of our canonical skills (proven by a
  ``*skills/<name>/SKILL.md`` path in git history). Safe to delete; prune targets these.
- **builtin** — lives only in a vendor's own skills dir (e.g. ~/.cursor/skills-cursor),
  shipped by that CLI. Reported, never touched.
- **untracked** — deployed in a shared dir but unknown to us (a manual/registry
  install). Reported, never auto-deleted — add it to external-skills.txt to keep it.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.result import StepResult

# Deployed skill directories we mirror, relative to $HOME. Codex + Pi share
# ~/.agents/skills; Cursor keeps its own (curated) set; Hermes has ~/.hermes/skills.
_SKILL_DIRS: tuple[tuple[str, ...], ...] = (
    (".claude", "skills"),
    (".agents", "skills"),
    (".codex", "skills"),
    (".cursor", "skills"),
    (".cursor", "skills-cursor"),
    (".hermes", "skills"),
)
# Dirs where our skills + external + untracked-external installs land. A skill that
# lives ONLY outside these (in a vendor's own dir) is that vendor's built-in.
_SHARED_LABELS = frozenset({".claude/skills", ".agents/skills"})

# Matches any historical skills path: `.ai/skills/<name>/SKILL.md`, `ai/skills/...`, etc.
_HISTORY_RE = re.compile(r"(?:^|/)skills/([^/]+)/SKILL\.md$")

OrphanOrigin = Literal["retired", "builtin", "untracked"]


class SkillOrphan(BaseModel):
    """A deployed skill dir not in the current canonical/external keep-set."""

    model_config = ConfigDict(frozen=True)

    location: str  # e.g. ".agents/skills"
    name: str
    path: str
    origin: OrphanOrigin  # retired = prune; builtin/untracked = keep


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


def deployed_locations(home: Path) -> dict[str, set[str]]:
    """name → the set of deployed dir labels it appears in (across all skill dirs)."""
    locations: dict[str, set[str]] = {}
    for parts in _SKILL_DIRS:
        target = home.joinpath(*parts)
        if not target.is_dir():
            continue
        label = "/".join(parts)
        for sub in target.iterdir():
            if sub.is_dir():
                locations.setdefault(sub.name, set()).add(label)
    return locations


def classify_orphan(name: str, ever_ours: set[str], locations: dict[str, set[str]]) -> OrphanOrigin:
    """retired (was ours) · builtin (only in a vendor dir) · untracked (everything else)."""
    if name in ever_ours:
        return "retired"
    locs = locations.get(name, set())
    if locs and not (locs & _SHARED_LABELS):
        return "builtin"
    return "untracked"


def find_orphans(runner: ProcessRunner, home: Path, dotfiles_dir: Path) -> list[SkillOrphan]:
    """Deployed skill dirs not in the canonical/external keep-set, classified by source."""
    keep = canonical_skill_names(dotfiles_dir) | external_skill_names(dotfiles_dir)
    ever_ours = ever_ours_names(runner, dotfiles_dir)
    locations = deployed_locations(home)
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
                    location=location,
                    name=sub.name,
                    path=str(sub),
                    origin=classify_orphan(sub.name, ever_ours, locations),
                )
            )
    return orphans


def prune_orphans(orphans: list[SkillOrphan], *, dry_run: bool) -> list[StepResult]:
    """Delete the retired orphans only (builtin + untracked are never touched)."""
    steps: list[StepResult] = []
    for orphan in (o for o in orphans if o.origin == "retired"):
        target = f"{orphan.location}/{orphan.name}"
        if dry_run:
            steps.append(StepResult(level="info", message=f"DRY RUN: rm {target}"))
        else:
            shutil.rmtree(orphan.path, ignore_errors=True)
            steps.append(StepResult(level="success", message=f"Removed {target}"))
    return steps
