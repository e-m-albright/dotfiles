# Code Health — persistent state

Durable, committed memory for the code-health skill book so passes are **stateful
and convergent across runs** instead of re-discovering the same findings. The
`converge` / `code-health` skills read this before diagnosing
and write to it after.

## Layout

One subdirectory per measured scope (a package or the repo):

```
docs/health/
  README.md            ← this file
  <scope>/
    baselines.json     ← the ratchet: metric ceilings, monotonic (only decrease)
    findings.md        ← the ledger: run log, open backlog, tolerated, dismissed
    report-<date>.md   ← graded U1–U11 health snapshot (diff future passes against it)
```

Current scopes: [`cli/`](cli/) (the `dotfiles` CLI + Mission Control TUI).

## The three artifacts

- **`baselines.json`** — counts that should only improve: LOC, per-family suppression counts, functions over the cognitive-complexity ceiling, dependency cycles. Each carries the grep/tool pattern that produced it, so the check is reproducible. Raising a ceiling needs an explicit `Ratchet-Bump:` commit trailer + reason (see [engineering-gates.md](../knowledge/engineering-gates.md) §1).
- **`findings.md`** — the decision memory: what was **fixed**, the ranked **open backlog** (deferred), what's **tolerated** by design (with an ADR link), and what was **dismissed** (investigated, not real). This is what answers "address vs tolerate vs newly-discovered."
- **`report-<date>.md`** — a graded snapshot against the `review` health rubric (U1–U11 + surface criteria), with an overall letter grade. Regenerated on a full pass; old ones stay for trend.

## How a pass uses it

1. **Read first.** Skip anything Tolerated; don't re-propose backlog items already recorded; load the last report for context.
2. **Diagnose**, marking each finding *known* (in backlog), *tolerated*, or *newly-discovered*.
3. **Fix** what's approved; **append** new findings; move fixed items to the run log.
4. **Lower `baselines.json`** to the new actuals (never raise silently); regenerate the report on a full pass.

Tolerated decisions with load-bearing rationale graduate to [`docs/adr/`](../adr/).

## Starting a new scope / repo

Run the engine in the target; it bootstraps `docs/health/<scope>/baselines.json` from the scorecard and seeds `findings.md`. Outside this repo the skill still works (the scorecard travels with it); commit the `docs/health/` it produces there so that repo gets the same durable memory.
