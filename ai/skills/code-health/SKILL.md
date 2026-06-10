---
name: code-health
description: The entry point and router for the code-health skill portfolio — diagnoses what a codebase needs and dispatches to the right lens, or sequences several for a full pass. Knows the form lenses (form-deepen, converge, form-tidy, form-clarify, form-align, form-prune, form-purify) and the function/safety/speed lenses (/review, /security-review, systematic-debugging, performance-engineer), their antagonists, and which are safe to run unattended. Use when the user says "improve code health", "where do I start", "do a full health pass", "audit and improve this repo", "which refactoring should I do here", or isn't sure which lens fits. SKIP when the user already named a specific lens — invoke that one directly.
---

# Code Health

The **router** for the code-health portfolio. Reach for it when the goal is "make this healthier" but the right move isn't obvious, or when you want a coordinated multi-lens pass. It diagnoses the symptom, picks the lens, sequences a pass, and — crucially — keeps the lenses from fighting each other.

## The completeness model: form vs. function

Read this first, because it sets honest expectations. Code quality has four source-measurable pillars (CISQ/ISO 5055): **Reliability, Performance, Security, Maintainability.** Refactoring is *behavior-preserving by definition*, so the refactor lenses below address essentially **only Maintainability** — they make code well-formed, not correct, secure, or fast. A refactor-only pass can even *introduce* security regressions.

So the portfolio is two tiers, and a real "health pass" needs both:

- **Tier A — form (behavior-preserving refactor lenses):** make it well-structured, idiomatic, legible, minimal.
- **Tier B — function / safety / speed (non-behavior-preserving):** find defects, vulnerabilities, and bottlenecks. These are existing skills — `/review`, `/security-review`, `systematic-debugging`, `performance-engineer` — not refactors. **Robustness comes from Tier B plus real test coverage, never from Tier A alone.**

State this to the user when they ask for "unimpeachable" code: the book guarantees form; correctness and safety rest on Tier B and tests.

## Tier A routing — pick by symptom

| Symptom / request | Lens | Axis |
|---|---|---|
| "this area's design feels wrong", coupled, shallow modules, conversational | **form-deepen** | taste · divergent |
| whole-repo, measured, ratchet down, reduce LOC, converge over passes | **converge** | measured · convergent |
| "clean up this function", extract, flatten conditionals, a known transform | **form-tidy** | mechanical · convergent |
| "hard to follow", naming, comments, newcomer/agent comprehension | **form-clarify** | taste · readability |
| names don't match the business, leaked API names, wrong boundaries | **form-align** | conceptual · divergent |
| over-engineered, dead code, YAGNI, "make it smaller" | **form-prune** | minimalist · convergent |
| "can only test end-to-end", tame side effects, illegal states | **form-purify** | testability · structural |

For a **single area**, route to one lens. For a **full pass**, sequence them (next section).

## The convergent sequence (full pass)

Lenses have a natural order that minimizes rework:

1. **form-prune** — delete first; never restructure code you could remove. Smaller surface for everything after.
2. **form-align** + **form-deepen** — get the concepts and boundaries right (diverge: find the real design).
3. **form-purify** — isolate effects so what remains is testable.
4. **form-tidy** — execute the mechanical transforms safely.
5. **form-clarify** — final readability and navigation pass.
6. **converge** — measure, ratchet the gains into CI contracts, and re-grade. This is what makes the pass *stick* and *converge* rather than re-rot.
7. **Tier B** — `/review`, `/security-review`, `systematic-debugging`, `performance-engineer` for the pillars refactoring can't reach.

Don't run all seven blindly — let the Tier-A routing table and the scorecard pick where effort actually pays (churn × complexity hotspots).

## Keeping lenses from fighting

The lenses genuinely contradict (dedup↔decouple, deepen↔prune, DDD-richness↔YAGNI). Two shared rules, enforced by every lens:

- **Rejected-decision log.** Before proposing, read the ADR log (`docs/adr/`) for decisions already declined; never re-litigate them. When a lens rejects a move for a load-bearing reason, write it back. This is the memory that stops successive passes and sibling lenses from undoing each other.
- **Arbitration, not accretion.** When two lenses recommend opposite edits on the same code, surface the tradeoff and decide *once*, recording it — don't let whichever ran last win.

## Scheduling policy (what's safe unattended)

Generative, structural refactoring on a weekly cron, auto-merged, is an anti-pattern — empirically it produces cosmetic churn with no measured health gain and a review backlog. So:

- **Safe unattended (weekly):** the `scorecard`/audit **detection** run that opens an issue or draft PR (never auto-merge); **ratchet enforcement** in CI (block regressions); deterministic **codemods** (`form-tidy`'s ast-grep/OpenRewrite transforms).
- **Interactive / human-gated:** `form-deepen`, `form-align`, `form-prune`, `form-purify`, and the engine's structural moves; all of Tier B. These are judgment- and conflict-heavy; they need a human and the arbitration rules above.

This mirrors how `ai/audits/` already run on a cadence: schedule the *finding*, gate the *fixing*.

## See also
- The measured engine and its references (metrics, ratchet, de-slop catalog, ontology, deepening vocab): [converge](../converge/SKILL.md).
- Shared canon: [docs/engineering-philosophy.md](../../../docs/engineering-philosophy.md) (12 principles), [docs/knowledge/engineering-gates.md](../../../docs/knowledge/engineering-gates.md) (ratchet mechanics), [docs/knowledge/code-health-portfolio.md](../../../docs/knowledge/code-health-portfolio.md) (the portfolio rationale and lens map).
