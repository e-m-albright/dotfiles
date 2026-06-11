"""The code-health Catechism: the doctrine backbone + symptom → rite routing.

Three layers, all printed by ``dotfiles agent catechism``:
- **Doctrine** — the curated hierarchy (Canon → Philosophy → Gates → Portfolio →
  per-scope health) that every quality effort hangs off. The machine-readable
  index of the docs that ARE the doctrine.
- **Live health** — the recorded ratchet floor per scope, read from
  ``docs/health/<scope>/baselines.json`` (LOC, complexity, suppression ceilings).
- **Router** — the call-and-response of symptom → rite (the entry-point map; the
  prose table in code-health-portfolio.md mirrors it).

See ENGINEERING.md for the umbrella framing.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dotfiles.cmd.agent.config import load_config
from dotfiles.cmd.agent.models import CatechismEntry
from dotfiles.fsutil import list_dir


class DoctrineLayer(BaseModel):
    """One layer of the code-health doctrine hierarchy: a curated doc + its role."""

    model_config = ConfigDict(frozen=True)

    name: str
    doc: str  # repo-relative path to the curated source
    role: str  # one line: what this layer is for


# The backbone, outermost → innermost. Each layer is a real curated doc; this is
# the index that makes the doctrine navigable (and lets us evolve it in one place).
DOCTRINE: tuple[DoctrineLayer, ...] = (
    DoctrineLayer(
        name="Canon",
        doc="ENGINEERING.md",
        role="the engineering map — doctrine, enforcement, layers, tools",
    ),
    DoctrineLayer(
        name="Philosophy",
        doc="docs/engineering-philosophy.md",
        role="the 12 universal code-health principles",
    ),
    DoctrineLayer(
        name="Gates",
        doc="docs/knowledge/engineering-gates.md",
        role="how each principle is enforced mechanically",
    ),
    DoctrineLayer(
        name="Defense map",
        doc="docs/knowledge/how-we-build.md",
        role="every gate/rite by layer (author→commit→push→CI→cadence)",
    ),
    DoctrineLayer(
        name="Portfolio",
        doc="docs/knowledge/code-health-portfolio.md",
        role="the lenses + the entry-point map (the router below)",
    ),
    DoctrineLayer(
        name="Assessment",
        doc="docs/health/ASSESSMENT.md",
        role="the independent, non-sycophantic review of the whole system",
    ),
)


class _ComplexityBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cognitive_max: int = 0
    functions_over_9: int = 0


class _BaselinesFile(BaseModel):
    """The fields of docs/health/<scope>/baselines.json the catechism surfaces."""

    model_config = ConfigDict(extra="ignore")

    scope: str = ""
    updated: str = ""
    loc_nontest: int = 0
    complexity: _ComplexityBlock = Field(default_factory=_ComplexityBlock)
    suppressions: dict[str, int] = Field(default_factory=dict)


class ScopeHealth(BaseModel):
    """The recorded ratchet floor for one health scope (read-only snapshot)."""

    model_config = ConfigDict(frozen=True)

    scope: str
    loc: int
    complexity_max: int
    complexity_over: int
    suppressions: dict[str, int]
    updated: str


def read_scope_health(dotfiles_dir: Path) -> list[ScopeHealth]:
    """Every docs/health/<scope>/baselines.json, parsed to a ScopeHealth snapshot."""
    health_root = dotfiles_dir / "docs" / "health"
    scopes: list[ScopeHealth] = []
    for entry in list_dir(health_root):
        baselines = entry / "baselines.json"
        if not entry.is_dir() or not baselines.is_file():
            continue
        cfg = load_config(baselines, _BaselinesFile)
        if cfg is None:
            continue
        scopes.append(
            ScopeHealth(
                scope=cfg.scope or entry.name,
                loc=cfg.loc_nontest,
                complexity_max=cfg.complexity.cognitive_max,
                complexity_over=cfg.complexity.functions_over_9,
                suppressions=dict(cfg.suppressions),
                updated=cfg.updated,
            )
        )
    return scopes


# Ordered front-door-first, then Tier A (form), then Tier B (function), then tooling.
CATECHISM: tuple[CatechismEntry, ...] = (
    CatechismEntry(
        symptom="not sure — systematic-debugging what this repo needs",
        rite="code-health",
        tier="router",
    ),
    CatechismEntry(
        symptom="measurably converge a whole repo + ratchet it in",
        rite="converge",
        tier="A · measured engine",
    ),
    CatechismEntry(
        symptom="think through one area's design, conversationally",
        rite="form-deepen",
        tier="A · taste",
    ),
    CatechismEntry(
        symptom="make it smaller — delete dead/speculative code",
        rite="form-prune",
        tier="A · deletion",
    ),
    CatechismEntry(
        symptom="make the code reflect the business domain", rite="form-align", tier="A · domain"
    ),
    CatechismEntry(
        symptom="make a tangled unit testable (pure core / effects out)",
        rite="form-purify",
        tier="A · testability",
    ),
    CatechismEntry(
        symptom="apply a known safe refactoring (extract, guard clauses…)",
        rite="form-tidy",
        tier="A · mechanical",
    ),
    CatechismEntry(
        symptom="make it readable to a newcomer / navigable by an agent",
        rite="form-clarify",
        tier="A · readability",
    ),
    CatechismEntry(
        symptom="make already-correct, already-clear code genuinely elegant",
        rite="code-style",
        tier="A · aesthetic",
    ),
    CatechismEntry(
        symptom="find bugs + grade a diff before merge", rite="review", tier="B · correctness"
    ),
    CatechismEntry(
        symptom="audit specifically for vulnerabilities",
        rite="/security-review",
        tier="B · security",
    ),
    CatechismEntry(
        symptom="chase a known failing test / hard bug",
        rite="systematic-debugging",
        tier="B · debugging",
    ),
    CatechismEntry(symptom="make it faster", rite="performance-engineer", tier="B · speed"),
    CatechismEntry(
        symptom="bootstrap a repo's health backbone (baselines + ledger)",
        rite="dotfiles agent health",
        tier="tooling",
    ),
)
