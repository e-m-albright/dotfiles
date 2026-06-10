"""Skill collision audit for repo-owned skills vs Pi package skills.

This is intentionally deterministic and conservative. It does not ask a model to
judge semantic overlap; it flags exact name shadowing and a small curated set of
workflow domains where two skills are likely to compete for the same user intent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.cmd.agent.config import load_config
from dotfiles.cmd.agent.skill_inventory import description

SourceKind = Literal["canonical", "pi-package"]
CollisionKind = Literal["same-name", "domain-overlap"]


class SkillSurface(BaseModel):
    """A skill visible to an agent, with its verifiable source."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    source_kind: SourceKind
    source: str
    path: str


class SkillCollision(BaseModel):
    """A likely trigger/intent collision between a local and external skill."""

    model_config = ConfigDict(frozen=True)

    kind: CollisionKind
    domain: str
    local: SkillSurface
    external: SkillSurface
    reason: str


class SkillCollisionReport(BaseModel):
    """The full collision audit result."""

    model_config = ConfigDict(frozen=True)

    local_count: int
    external_count: int
    collisions: tuple[SkillCollision, ...]


_DOMAIN_OVERRIDES: dict[str, frozenset[str]] = {
    "collaborative-ideation": frozenset({"brainstorm"}),
    "planning": frozenset({"plan"}),
    "workflow-closeout-learning": frozenset({"finish"}),
}

_DOMAIN_TERMS: dict[str, frozenset[str]] = {
    "brainstorm": frozenset(
        {"brainstorm", "brainstorming", "ideation", "socratic", "requirements"}
    ),
    "plan": frozenset({"plan", "plans", "planning", "scope", "implementation"}),
    "execute": frozenset({"execute", "executing", "implementation"}),
    "verify": frozenset({"verify", "verification", "evidence", "passing"}),
    "review": frozenset({"review", "reviewer", "audit", "pre-merge"}),
    "debug": frozenset({"debug", "debugging", "diagnose", "diagnosis", "failing"}),
    "tdd": frozenset({"tdd", "test-driven", "red-green", "refactor"}),
    "worktree": frozenset({"worktree", "worktrees"}),
    "finish": frozenset({"finish", "finishing", "ship", "shipping", "merge"}),
    "github": frozenset({"github", "gh", "pull-request", "pr"}),
    "browser": frozenset({"browser", "playwright", "chrome", "web-browser"}),
    "frontend": frozenset({"frontend", "ui", "design"}),
    "uv": frozenset({"uv", "python"}),
    "mermaid": frozenset({"mermaid", "diagram"}),
    "commit": frozenset({"commit", "commits"}),
    "summarize": frozenset({"summarize", "summary", "markdown"}),
}


def _norm(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else " " for ch in text)


def _domains(skill: SkillSurface) -> set[str]:
    # Be conservative: collisions should be actionable. Skill descriptions often
    # include long routing notes ("SKIP for /review", "not for debugging") that
    # make broad text similarity noisy, so derive domains from names only.
    haystack = _norm(skill.name)
    tokens = set(haystack.split())
    compact = haystack.replace(" ", "-")
    found: set[str] = set(_DOMAIN_OVERRIDES.get(skill.name, frozenset()))
    for domain, terms in _DOMAIN_TERMS.items():
        for term in terms:
            term_norm = _norm(term).strip()
            is_phrase = "-" in term or " " in term
            if term_norm in tokens or (is_phrase and term in compact):
                found.add(domain)
                break
    return found


def local_skill_surfaces(dotfiles_dir: Path) -> list[SkillSurface]:
    """Repo-owned canonical skills under ``ai/skills``."""
    root = dotfiles_dir / "ai" / "skills"
    if not root.is_dir():
        return []
    out: list[SkillSurface] = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        out.append(
            SkillSurface(
                name=skill_md.parent.name,
                description=description(skill_md),
                source_kind="canonical",
                source="ai/skills",
                path=str(skill_md.relative_to(dotfiles_dir)),
            )
        )
    return out


class _PiManifest(BaseModel):
    """The ``pi`` block of a package.json — only the ``skills`` roots we need."""

    model_config = ConfigDict(extra="ignore")

    skills: list[str] = []


class _PackageJson(BaseModel):
    """Just the ``pi`` manifest of a package.json (extra keys ignored)."""

    model_config = ConfigDict(extra="ignore")

    pi: _PiManifest | None = None


class _PiSettings(BaseModel):
    """The Pi settings keys relevant to package activation."""

    model_config = ConfigDict(extra="ignore")

    packages: list[str] | None = None


def _package_skill_roots(package_dir: Path) -> list[Path]:
    cfg = load_config(package_dir / "package.json", _PackageJson)
    if cfg is None or cfg.pi is None:
        return []
    return [package_dir / root for root in cfg.pi.skills]


def _surfaces_in_package(package_dir: Path, home: Path) -> list[SkillSurface]:
    """The Pi-package skill surfaces declared by one node_modules package."""
    out: list[SkillSurface] = []
    for root in _package_skill_roots(package_dir):
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            out.append(
                SkillSurface(
                    name=skill_md.parent.name,
                    description=description(skill_md),
                    source_kind="pi-package",
                    source=package_dir.name,
                    path=str(skill_md.relative_to(home)),
                )
            )
    return out


def _active_pi_package_names(home: Path) -> set[str] | None:
    """Active package names from Pi settings, or None when settings is absent.

    ``None`` keeps audits useful in synthetic/test homes without a settings file;
    an explicit empty package list means no package skills are active.
    """
    cfg = load_config(home / ".pi" / "agent" / "settings.json", _PiSettings)
    if cfg is None or cfg.packages is None:
        return None
    names: set[str] = set()
    for item in cfg.packages:
        name = item.removeprefix("npm:")
        if name:
            names.add(name)
    return names


def pi_package_skill_surfaces(home: Path) -> list[SkillSurface]:
    """Skills shipped by active Pi npm packages.

    Scans package metadata instead of every dependency, so transitive packages do
    not look like agent skills just because they contain Markdown. If Pi settings
    has a ``packages`` array, only those active packages are scanned.
    """
    packages_root = home / ".pi" / "agent" / "npm" / "node_modules"
    if not packages_root.is_dir():
        return []
    active_packages = _active_pi_package_names(home)
    out: list[SkillSurface] = []
    for package_dir in sorted(p for p in packages_root.iterdir() if p.is_dir()):
        if package_dir.name.startswith("."):
            continue
        if active_packages is not None and package_dir.name not in active_packages:
            continue
        out.extend(_surfaces_in_package(package_dir, home))
    return out


def collision_report(*, home: Path, dotfiles_dir: Path) -> SkillCollisionReport:
    """Find likely collisions between canonical skills and Pi package skills."""
    locals_ = local_skill_surfaces(dotfiles_dir)
    externals = pi_package_skill_surfaces(home)
    collisions: list[SkillCollision] = []

    for local in locals_:
        local_domains = _domains(local)
        for external in externals:
            if local.name == external.name:
                domain = next(iter(sorted(local_domains | _domains(external))), "name")
                collisions.append(
                    SkillCollision(
                        kind="same-name",
                        domain=domain,
                        local=local,
                        external=external,
                        reason="same skill name is available from a Pi package and ai/skills",
                    )
                )
                continue
            shared = sorted(local_domains & _domains(external))
            for domain in shared:
                collisions.append(
                    SkillCollision(
                        kind="domain-overlap",
                        domain=domain,
                        local=local,
                        external=external,
                        reason=f"both skills advertise the {domain!r} workflow/domain",
                    )
                )

    collisions.sort(
        key=lambda c: (c.domain, c.kind, c.local.name, c.external.source, c.external.name)
    )
    return SkillCollisionReport(
        local_count=len(locals_),
        external_count=len(externals),
        collisions=tuple(collisions),
    )
