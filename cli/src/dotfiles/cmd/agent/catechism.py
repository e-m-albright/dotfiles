"""The code-health Catechism: the call-and-response routing of symptom → rite.

This is the machine-readable source of the entry-point map; the prose table in
docs/knowledge/code-health-portfolio.md mirrors it. Printed by
``dotfiles agent catechism``. See CANON.md for the umbrella framing.
"""

from __future__ import annotations

from dotfiles.cmd.agent.models import CatechismEntry

# Ordered front-door-first, then Tier A (form), then Tier B (function), then tooling.
CATECHISM: tuple[CatechismEntry, ...] = (
    CatechismEntry(
        symptom="not sure — diagnose what this repo needs", rite="code-health", tier="router"
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
        symptom="find bugs + grade a diff before merge", rite="review", tier="B · correctness"
    ),
    CatechismEntry(
        symptom="audit specifically for vulnerabilities",
        rite="/security-review",
        tier="B · security",
    ),
    CatechismEntry(
        symptom="chase a known failing test / hard bug", rite="diagnose", tier="B · debugging"
    ),
    CatechismEntry(symptom="make it faster", rite="performance-engineer", tier="B · speed"),
    CatechismEntry(
        symptom="bootstrap a repo's health backbone (baselines + ledger)",
        rite="dotfiles agent health",
        tier="tooling",
    ),
)
