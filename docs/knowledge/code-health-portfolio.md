# The Code-Health Canon & Catechism

> A curated set of *contestable* lenses for improving a codebase, not a unified theory. Routed by the [`code-health`](../../ai/skills/code-health/SKILL.md) skill. Enforced by the ratchet in [engineering-gates.md](engineering-gates.md); graded against [engineering-philosophy.md](../engineering-philosophy.md).

## The Canon & the Catechism

> This page is the **code-health** chapter of a repo-wide frame. The full umbrella — process, code health, DX, and the toolbelt — lives at [`CANON.md`](../../CANON.md). What follows applies the same two-halves lens to code health specifically.

The whole system has two halves. Naming them makes the umbrella easy to hold in one's head — and easy to keep honest, because they answer different questions.

- **The Canon** — *what is true about good code.* The doctrine you don't relitigate every PR: the [12 Principles](../engineering-philosophy.md), the [gates that enforce each](engineering-gates.md), the [form/function completeness model](#the-completeness-model-form-vs-function) below, the arbitrated [antagonist tiebreaks](#the-lenses), and the [evidence base](#evidence-base). The Canon answers **why**. It changes rarely, and only by argument.
- **The Catechism** — *what you actually do, confronted with real code.* The drilled practice: the lenses (`form-*`, `converge`, Tier B), the [ratchet and routines](../health/README.md#routines--what-makes-it-self-managing), the persistent [health state](../health/README.md), and the call-and-response [entry-point map](#entry-points--the-catechism) — literally question→answer ("want to make it smaller? → `form-prune`"). The Catechism answers **what do I do now**.

Mnemonic: **believe the Canon, practice the Catechism.** A catechism is just doctrine made drillable — the Catechism here is the Canon rendered executable: every rite (a lens, a gate, a routine) traces back to a principle, and every principle has at least one rite that enacts it. If a practice can't be traced to the Canon, it's superstition; if a principle has no practice, it's a claim the system can't keep (which is exactly what [engineering-philosophy.md](../engineering-philosophy.md) means by "if you cannot enforce it, do not claim it").

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
| **form-deepen** | Ousterhout — deep modules | taste · divergent | vs tidy/Clean-Code over-decomposition → prefer depth |
| **converge** | empirical SE — fitness functions, ratchet | measured · convergent | the orchestrator; ratchets the rest in |
| **form-tidy** | Fowler/Beck — refactoring catalog, two-hats | mechanical · convergent | vs deepen → extract for a real seam, not a line target |
| **form-clarify** | Buse-Weimer + Scalabrino — readability | taste · readability | vs prune → keep the *why*, cut restating |
| **form-align** | Evans DDD — ubiquitous language, contexts | conceptual · divergent | vs YAGNI → richness only in the core subdomain |
| **form-prune** | minimalism — YAGNI, worse-is-better, Tigerstyle | minimalist · convergent | vs structure-adders → delete first, then build |
| **form-purify** | FP/hexagonal — pure core, parse-don't-validate | testability · structural | vs YAGNI → isolate effects only where they block testing |

### Tier B — function / safety / speed (non-behavior-preserving, existing skills)

`/review` (correctness, defects, health grade) · `/security-review` (vulnerabilities) · `diagnose` (hard bugs, regressions) · `performance-engineer` (bottlenecks). These find or change behavior; they are not refactors.

## Substrate legend (what kind of thing each lens is)

The lenses are deliberately different *kinds* of artifact, invoked differently. The router (`code-health`) hides this, but when reaching for one directly:

| Kind | How you invoke it | Which lenses |
|---|---|---|
| **Skill** | name or `/name` (auto-fires on triggers) | `code-health`, `converge`, `form-deepen`, `form-tidy`, `form-prune`, `form-clarify`, `form-align`, `form-purify`, `review`, `diagnose` |
| **Slash command** | typed `/name` only (built-in) | `/security-review`, `/simplify` |
| **Subagent** | dispatched via the Agent tool | `performance-engineer` |

A newcomer should start at the **`code-health` router** and let it dispatch; reach for a specific lens directly only when you already know the one you want.

## Entry points — the Catechism

The call-and-response of the system: a symptom on the left, the rite to reach for on the right. The single front door is **`code-health`** (when unsure, start there and let it dispatch). Past it, pick by what you actually want:

| You want to… | Reach for | Tier · kind |
|---|---|---|
| not sure — diagnose what this repo needs | **`code-health`** | router |
| measurably converge a whole repo + ratchet it in | **`converge`** | A · measured engine |
| think through *one area's* design, conversationally | **`form-deepen`** | A · taste |
| make it smaller — delete dead/speculative code | **`form-prune`** | A · deletion |
| make the code reflect the business domain | **`form-align`** | A · domain |
| make a tangled unit testable (pure core / effects out) | **`form-purify`** | A · testability |
| apply a known safe refactoring (extract, guard clauses…) | **`form-tidy`** | A · mechanical |
| make it readable to a newcomer / navigable by an agent | **`form-clarify`** | A · readability |
| find bugs + grade a diff before merge | **`review`** | B · correctness |
| audit specifically for vulnerabilities | **`/security-review`** | B · security |
| chase a known failing test / hard bug | **`diagnose`** | B · debugging |
| make it faster | **`performance-engineer`** | B · speed |
| bootstrap a repo's health backbone (baselines + ledger) | **`dotfiles agent health`** | tooling |

The one overlap to know: a bare *"this feels coupled / where are the seams?"* fits **both** `converge` (whole-repo, measured) and `form-deepen` (one area, conversational) — add a scope word, or let the router decide.

## The convergent sequence (full pass)

`form-prune` (delete first) → `form-align` + `form-deepen` (get concepts/boundaries right) → `form-purify` (make it testable) → `form-tidy` (mechanical transforms) → `form-clarify` (readability) → `converge` (measure, ratchet into CI contracts, re-grade) → Tier B (pillars refactoring can't reach). Let the churn×complexity scorecard pick where effort pays; don't run all of it blindly.

## Shared conventions (what keeps it convergent)

1. **Rejected-decision log.** Every lens reads `docs/adr/` for declined moves before proposing, and writes back load-bearing rejections. This is the memory that stops passes and sibling lenses from undoing each other — the single highest-leverage anti-oscillation mechanism.
2. **Arbitration, not accretion.** Contradictory moves on the same code surface the tradeoff and get decided once and recorded — never resolved by whichever ran last.
3. **Quality ratchet.** Metrics may hold or improve, never regress (committed baselines, monotonic guard). The safe substrate for any continuous run. See [engineering-gates.md](engineering-gates.md).
4. **Persistent health state.** Each run reads and writes a committed `docs/health/<scope>/` — `baselines.json` (the ratchet numbers), `findings.md` (fixed / open backlog / tolerated / dismissed), and `report-<date>.md` (graded snapshot). This is what makes passes *stateful and convergent across runs* instead of re-discovering the same findings; see [health/README.md](../health/README.md).

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
