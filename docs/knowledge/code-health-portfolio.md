# The Code-Health Skill Portfolio

> A curated set of *contestable* lenses for improving a codebase, not a unified theory. Routed by the [`code-health`](../../ai/skills/code-health/SKILL.md) skill. Enforced by the ratchet in [engineering-gates.md](engineering-gates.md); graded against [engineering-philosophy.md](../engineering-philosophy.md).

## Why a portfolio instead of one skill

Two axes, not one. **Convergent↔divergent** (does it narrow toward a fixed target or open new possibilities?) and **measured↔taste** (is "better" gated by a number or by judgment?). A single skill can't sit in two places at once, and the two ends do genuinely different work:

- **Measured/convergent** buys guarantees — anti-regression, "prove it improved," termination — but is blind to taste and can suppress the bold rewrite a metric reads as a spike.
- **Taste/divergent** finds the leaps no metric sees — the wrong metaphor, the elegant collapse — but doesn't converge and isn't regression-safe.

The reconciliation: **safety is always measured (tests, behavior preservation); betterness is measured where it can be and human-gated where it can't — and the human-gated decision is recorded as an ADR so it becomes durable.** That ADR is the ratchet for the unmeasurable. This is why a pure-taste lens is legitimate, not a worse version of the measured one.

## The completeness model: form vs. function

Code quality has four source-measurable pillars (CISQ/ISO 5055): **Reliability, Performance, Security, Maintainability.** Refactoring is behavior-preserving by definition, so the Tier-A lenses address essentially **only Maintainability**. They make code well-formed — not correct, secure, or fast — and can even *introduce* security regressions. Robustness comes from **Tier B + real test coverage**, never from Tier A alone. Don't let the book imply a guarantee it structurally can't make.

## The lenses

### Tier A — form (behavior-preserving)

| Skill | School / lineage | Axis | Primary antagonist + tiebreak |
|---|---|---|---|
| **deepen** | Ousterhout — deep modules | taste · divergent | vs tidy/Clean-Code over-decomposition → prefer depth |
| **improve-codebase-architecture** | empirical SE — fitness functions, ratchet | measured · convergent | the orchestrator; ratchets the rest in |
| **tidy** | Fowler/Beck — refactoring catalog, two-hats | mechanical · convergent | vs deepen → extract for a real seam, not a line target |
| **legible** | Buse-Weimer + Scalabrino — readability | taste · readability | vs prune → keep the *why*, cut restating |
| **domain-align** | Evans DDD — ubiquitous language, contexts | conceptual · divergent | vs YAGNI → richness only in the core subdomain |
| **prune** | minimalism — YAGNI, worse-is-better, Tigerstyle | minimalist · convergent | vs structure-adders → delete first, then build |
| **functional-core** | FP/hexagonal — pure core, parse-don't-validate | testability · structural | vs YAGNI → isolate effects only where they block testing |

### Tier B — function / safety / speed (non-behavior-preserving, existing skills)

`/review` (correctness, defects, health grade) · `/security-review` (vulnerabilities) · `diagnose` (hard bugs, regressions) · `performance-engineer` (bottlenecks). These find or change behavior; they are not refactors.

## The convergent sequence (full pass)

`prune` (delete first) → `domain-align` + `deepen` (get concepts/boundaries right) → `functional-core` (make it testable) → `tidy` (mechanical transforms) → `legible` (readability) → `improve-codebase-architecture` (measure, ratchet into CI contracts, re-grade) → Tier B (pillars refactoring can't reach). Let the churn×complexity scorecard pick where effort pays; don't run all of it blindly.

## Shared conventions (what keeps it convergent)

1. **Rejected-decision log.** Every lens reads `docs/adr/` for declined moves before proposing, and writes back load-bearing rejections. This is the memory that stops passes and sibling lenses from undoing each other — the single highest-leverage anti-oscillation mechanism.
2. **Arbitration, not accretion.** Contradictory moves on the same code surface the tradeoff and get decided once and recorded — never resolved by whichever ran last.
3. **Quality ratchet.** Metrics may hold or improve, never regress (committed baselines, monotonic guard). The safe substrate for any continuous run. See [engineering-gates.md](engineering-gates.md).

## Scheduling policy

Generative, structural refactoring on a weekly cron, auto-merged, is an anti-pattern: empirically it yields cosmetic churn, no measured health gain, ~half the PRs needing fixes, and inter-pass oscillation.

- **Safe unattended (weekly):** detection runs (`scorecard.sh`, `ai/audits/`) that open an issue/draft PR, never auto-merge; ratchet enforcement in CI; deterministic codemods.
- **Interactive / human-gated:** every taste/structural Tier-A lens and all of Tier B. Schedule the *finding*; gate the *fixing*.

## Evidence base

- *Agentic Refactoring: An Empirical Study of AI Coding Agents* — [arXiv 2511.04824](https://arxiv.org/html/2511.04824v1) (unattended agent refactoring is cosmetic; 53.9% scope-creep; smell count unchanged).
- CISQ / ISO 5055 four pillars — [it-cisq.org](https://www.it-cisq.org/cisq-files/pdf/CISQ-and-ISO-25000.pdf).
- CodeScene *Code Red* — [arXiv 2203.04374](https://arxiv.org/abs/2203.04374) (low health → 15× defects, 2.24× dev time; hotspots = churn×complexity).
- GitClear *AI Copilot Code Quality 2025* (duplication up ~8×; "moved"/refactored code 24%→9.5%).
- Readability as a dimension — Buse & Weimer (ISSTA'08/TSE'10); Scalabrino et al. (JSEP'18, and ASE'17: no readability score is a valid target).
- Ousterhout *A Philosophy of Software Design* vs Martin *Clean Code* — [the debate](https://github.com/johnousterhout/aposd-vs-clean-code) (deep modules vs small functions; the deepen↔tidy tension).
- Metz, *The Wrong Abstraction*; Dodds, *AHA Programming* (dedup vs coupling).
- Mikado Method; *Software Engineering at Google* ch. 22 (large-scale change, cleanup+prevention).
