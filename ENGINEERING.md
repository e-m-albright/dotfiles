# How We Build — the Engineering Map

> The single source of truth for how this repo builds: what we believe, how it's
> enforced, where it fires, and what you reach for. One screen, one nesting.
>
> **Spoken alias:** when the owner says **"the Canon,"** he means *this whole map* —
> the doctrine and its enforcement, taken together. The word is a handle, not a layer.

---

## The map

Read it left to right as one sentence: **a *principle* is caught by a *gate* that fires
at a *layer* where you reach for a *lens* — and the *ratchet* makes the win stick.**

```
                THE ENGINEERING MAP   ·   how we build, in one screen

   DOCTRINE                ENFORCEMENT            DEFENSE IN DEPTH          TOOLS
   what we believe   ─►    how it's caught  ─►    where & when it fires ─►  what you reach for
  ┌────────────────┐      ┌───────────────┐      ┌──────────────────┐     ┌────────────────┐
  │ Kernel  K1–K8  │      │ Gates  G1–G14 │      │ L0 author-time   │     │ form-* lenses  │
  │ Principles     │ ──►  │ (enforcement  │ ──►  │ L1 pre-commit  ▓ │ ──► │ converge       │
  │   P1–P12       │      │  doctrine)    │      │ L2 pre-push    ▓ │     │ review · /sec  │
  └────────────────┘      └───────────────┘      │ L3 CI          ▓ │     │ debugging·perf │
    every Principle         each P maps to        │ L4 scheduled     │     └────────────────┘
    is a belief we          ≥1 Gate that          │ L5 convergence   │       reached for at
    don't relitigate        enforces it           └──────────────────┘       L0 · L4 · L5
                                          ▓ = blocking
        ╞═══════════════════ THE RATCHET — the bridge ═══════════════════╡
         a stochastic win (a lens deepens a module, an audit finds slop you delete)
         becomes a deterministic floor the next change can't breach. Fires at L1·L2·L3.
```

**The binding law:** every Principle has an enforcement — a deterministic **Gate** where
one is possible, a **review** check (Tier B) where the property is irreducibly semantic
(e.g. P8, concurrency bounds). A belief with *neither* is a claim we can't keep — *if you
cannot enforce it, do not claim it.* A gate with no belief behind it is ceremony. The four columns are
one system seen from four angles.

**Two readings of the same picture:**
1. **Shift-left (the layers).** Catch each defect at the cheapest layer that can: a type
   error dies in the editor (L0), a style drift at pre-commit (L1), a broken test at
   pre-push (L2), a hookless contributor at CI (L3); slow rot is *found* on a schedule
   (L4) and *fixed* by convergence (L5).
2. **Deterministic spine, stochastic leaves.** The floor (L1–L3, the ratchet) is dumb,
   cheap, blocking, repeatable. The judgment (L0/L4/L5 — lenses, audits, reviews) is
   stochastic LLM work. They meet at **the ratchet**, the only thing that makes taste stick.

---

## Doctrine — what we believe

### The kernel · K1–K8 — how we work
*Full text: [`ai/agents/shared/rules.md`](ai/agents/shared/rules.md), deployed verbatim to every agent.*

| ID | Article |
|----|---------|
| **K1** | Verify before claiming done — evidence before assertions. |
| **K2** | Brainstorm before building; plan multi-step work. |
| **K3** | Minimize surface area — the smallest change that solves it. |
| **K4** | Build on bedrock, not quicksand — fix root causes; suppressions are never the first move. |
| **K5** | No competing versions — a replacement deletes its predecessor in the same change. |
| **K6** | Don't game metrics — satisfy the check's intent, never weaken it. |
| **K7** | Respect conventions; debug systematically — reproduce, hypothesize, test. |
| **K8** | No sycophancy; calibrate confidence — say what you know, flag what you don't. |

### The principles · P1–P12 — what good code is
*Full text + the gate for each: [`docs/engineering-philosophy.md`](docs/engineering-philosophy.md).*

| ID | Principle | Caught by |
|----|-----------|-----------|
| **P1** | The compiler is the first reviewer | G5, L0–L1 |
| **P2** | Type the domain, not the plumbing | L0 |
| **P3** | One source of truth per concept | G6, G11 |
| **P4** | Boundaries are contracts | G6 |
| **P5** | Simplicity is the goal — small files are a proxy | G1, G5 |
| **P6** | Dead code is dead weight | G1, L1 |
| **P7** | Every exception is an event | G13 |
| **P8** | Concurrency is bounded | review (Tier B) |
| **P9** | Observability is a design constraint | G13 |
| **P10** | Suppressions ratchet downward | G1 |
| **P11** | Tests verify behavior, not implementation | G5, G8 |
| **P12** | Convention over configuration over code | G3, G11 |

---

## Enforcement — the gates · G1–G14

*How each belief is made mechanical. Full text: [`docs/knowledge/engineering-gates.md`](docs/knowledge/engineering-gates.md) (sections 1–14 are G1–G14).*

| ID | Gate | Fires at |
|----|------|----------|
| **G1** | The baselines ratchet — the floor that only rises | L1·L2·L3 |
| **G2** | No competing versions | L1·L3 |
| **G3** | CI calls task-runner recipes; YAML holds zero logic | L3 |
| **G4** | Affectedness-based test selection | L2·L3 |
| **G5** | Coverage & complexity as ratcheting floors | L1·L2·L3 |
| **G6** | Contract codegen with a freshness gate | L3 |
| **G7** | A required aggregating gate that tolerates skips | L3 |
| **G8** | Cost-aware test taxonomy | L2·L3·L4 |
| **G9** | Hook-failure triage (when a gate blocks you) | L1·L2 |
| **G10** | Secrets & supply-chain gates | L1·L3 |
| **G11** | Fleet uniformity: one source, translated, drift-gated | L3 |
| **G12** | Reproducible, hermetic builds | L3 |
| **G13** | Fail loud, never silent in your own layer | L0·L3 |
| **G14** | Refactoring & deploy safety | L2·L3 |

---

## Defense in depth — the layers · L0–L5

*Where and when every gate fires, cheapest-first. Full detail: [`docs/knowledge/how-we-build.md`](docs/knowledge/how-we-build.md).*

| ID | Layer | What runs | D/S |
|----|-------|-----------|-----|
| **L0** | Author-time | types · LSP · compiler-as-first-reviewer; the AI pair (lenses, planning, TDD) | D + S |
| **L1** | Pre-commit | `just check --fast` — fmt → lint → types → deadcode → complexity → **ratchet** | D |
| **L2** | Pre-push | `just check` — everything above **+ tests, coverage ≥ 85** | D |
| **L3** | CI | the same recipes · shell/json/yaml · secrets scan · aggregating gate | D |
| **L4** | Scheduled | scorecard + audit skills → issue / draft PR. *Schedule the finding, gate the fixing.* | D + S |
| **L5** | Convergence | the `converge` engine, on demand: measure → fix → **lower the baselines** | S → D |

**The ratchet is the bridge.** A stochastic win at L0/L4/L5 is fragile until `converge`
records the new actuals as baselines — then it's a deterministic floor at L1–L3 that the
next change can't breach. *Taste, made durable.*

---

## Tools — the lenses

The contestable lenses for improving a codebase, routed by the
[`code-health`](ai/skills/code-health/SKILL.md) skill. Full theory — the two-axis model,
antagonist tiebreaks, the convergent sequence: [`docs/knowledge/code-health-portfolio.md`](docs/knowledge/code-health-portfolio.md).

- **Form (behavior-preserving):** `form-deepen` · `form-tidy` · `form-prune` ·
  `form-clarify` · `form-align` · `form-purify`, with `converge` as the measured engine.
- **Function / safety / speed:** `review` · `/security-review` · `systematic-debugging` ·
  `performance-engineer`. These find or change behavior — not refactors.

---

## Routing — symptom → rite

The front door is **`code-health`** (when unsure, start there and let it dispatch). Past
it, pick by what you actually want. `dotfiles agent catechism` prints this routing.

| You want to… | Reach for | Serves |
|--------------|-----------|--------|
| not sure — diagnose what this repo needs | **`code-health`** | router |
| measurably converge a whole repo + ratchet it in | **`converge`** | G1, P5 |
| think through *one area's* design, conversationally | **`form-deepen`** | P5 |
| make it smaller — delete dead/speculative code | **`form-prune`** | P6 |
| make the code reflect the business domain | **`form-align`** | P3 |
| make a tangled unit testable (pure core / effects out) | **`form-purify`** | P11 |
| apply a known safe refactoring (extract, guard clauses…) | **`form-tidy`** | P5 |
| make it readable to a newcomer / navigable by an agent | **`form-clarify`** | — |
| find bugs + grade a diff before merge | **`review`** | K1 |
| audit specifically for vulnerabilities | **`/security-review`** | G10 |
| chase a known failing test / hard bug | **`systematic-debugging`** | K7 |
| make it faster | **`performance-engineer`** | — |
| a gate blocked my commit/push | **`hook-failure-triage`** | G9 |
| bootstrap a repo's health backbone (baselines + ledger) | **`dotfiles agent health`** | G1 |

---

## Extending the map

> Every rite traces to a belief; every belief has a rite. Adding a practice means naming
> the Principle or Gate it serves (its ID), or it's ceremony. Adding a belief means naming
> the gate that will enforce it, or it's a claim we can't keep.

- The 12-principle deep text: [`docs/engineering-philosophy.md`](docs/engineering-philosophy.md).
- The enforcement deep text (G1–G14): [`docs/knowledge/engineering-gates.md`](docs/knowledge/engineering-gates.md).
- The layered defense-in-depth detail: [`docs/knowledge/how-we-build.md`](docs/knowledge/how-we-build.md).
- The lens portfolio + evidence base: [`docs/knowledge/code-health-portfolio.md`](docs/knowledge/code-health-portfolio.md).
- The independent critique of the code-health half: [`docs/health/ASSESSMENT.md`](docs/health/ASSESSMENT.md).
- Persistent health state convention: [`docs/health/README.md`](docs/health/README.md).
