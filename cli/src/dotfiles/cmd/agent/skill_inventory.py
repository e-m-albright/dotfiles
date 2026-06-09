"""Verifiable skill inventory: every available skill, its origin, and description.

Origin is derived from real state, never guessed:
- **canonical** — lives in this repo's ``ai/skills/`` (the source of truth).
- **external** — tracked in ``external-skills.txt`` (intentional third-party installs).
- **plugin** — shipped by an installed Claude Code plugin (installed_plugins.json).
- **builtin** — lives only in a vendor's own skills dir (e.g. ~/.cursor/skills-cursor).
- **retired** — was once one of our canonical skills (git history), since renamed/removed.
- **untracked** — deployed in a shared dir but unknown to us (a manual/registry install).

The description is the SKILL.md frontmatter ``description:`` line, read from the
canonical source (or the deployed/plugin copy for non-canonical skills).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.skill_prune import (
    canonical_skill_names,
    classify_orphan,
    deployed_locations,
    ever_ours_names,
    external_skill_names,
)

SkillOrigin = Literal["canonical", "external", "plugin", "builtin", "retired", "untracked"]

# Deployed skill dirs (relative to $HOME) scanned for non-canonical skills.
_DEPLOYED_DIRS: tuple[tuple[str, ...], ...] = (
    (".claude", "skills"),
    (".agents", "skills"),
    (".codex", "skills"),
    (".cursor", "skills-cursor"),
)

_DESC_RE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)


class SkillInfo(BaseModel):
    """One skill in the inventory, with verifiable origin + description."""

    model_config = ConfigDict(frozen=True)

    name: str
    origin: SkillOrigin
    description: str
    source: str  # repo path, external-skills.txt, or marketplace ref


def _description(skill_md: Path | None) -> str:
    """The frontmatter description line of a SKILL.md (empty if unreadable/absent)."""
    if skill_md is None or not skill_md.is_file():
        return ""
    try:
        text = skill_md.read_text()
    except OSError:
        return ""
    match = _DESC_RE.search(text)
    return match.group(1).strip().strip("\"'") if match else ""


def _plugin_skills(home: Path) -> dict[str, tuple[str, Path]]:
    """name → (marketplace ref, SKILL.md path) for skills shipped by installed plugins."""
    config = home / ".claude" / "plugins" / "installed_plugins.json"
    out: dict[str, tuple[str, Path]] = {}
    if not config.is_file():
        return out
    try:
        data = json.loads(config.read_text())
    except (OSError, json.JSONDecodeError):
        return out
    for ref, installs in data.get("plugins", {}).items():
        for install in installs:
            base = Path(install.get("installPath", ""))
            for skill_md in (*base.glob("skills/*/SKILL.md"), *base.glob("*/SKILL.md")):
                out.setdefault(skill_md.parent.name, (ref, skill_md))
    return out


def _deployed_skill_md(home: Path) -> dict[str, Path]:
    """name → a deployed SKILL.md path (first match wins), across all skill dirs."""
    found: dict[str, Path] = {}
    for parts in _DEPLOYED_DIRS:
        target = home.joinpath(*parts)
        if not target.is_dir():
            continue
        for sub in target.iterdir():
            if sub.is_dir() and (sub / "SKILL.md").is_file():
                found.setdefault(sub.name, sub / "SKILL.md")
    return found


def inventory(runner: ProcessRunner, home: Path, dotfiles_dir: Path) -> list[SkillInfo]:
    """Every known skill, alphabetical, classified by verifiable origin."""
    canonical = canonical_skill_names(dotfiles_dir)
    external = external_skill_names(dotfiles_dir)
    plugins = _plugin_skills(home)
    deployed = _deployed_skill_md(home)
    ever_ours = ever_ours_names(runner, dotfiles_dir)
    locations = deployed_locations(home)

    infos: list[SkillInfo] = []
    for name in sorted(canonical | external | set(plugins) | set(deployed)):
        if name in canonical:
            origin: SkillOrigin = "canonical"
            md: Path | None = dotfiles_dir / "ai" / "skills" / name / "SKILL.md"
            source = f"ai/skills/{name}"
        elif name in external:
            origin, md, source = "external", deployed.get(name), "external-skills.txt"
        elif name in plugins:
            ref, md = plugins[name]
            origin, source = "plugin", ref
        else:
            origin = classify_orphan(name, ever_ours, locations)
            md = deployed.get(name)
            source = (
                "was canonical (renamed/removed)"
                if origin == "retired"
                else ", ".join(sorted(locations.get(name, set())))
            )
        infos.append(
            SkillInfo(name=name, origin=origin, description=_description(md), source=source)
        )
    return infos
