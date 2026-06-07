# Metrics & the Ratchet

What to measure, how to rank by it, and how to lock improvements in. The principle throughout: **gate the delta, not the backlog** — grandfather existing debt, block regressions, ratchet the ceiling down over time. This is what makes the discipline adoptable on a real codebase instead of a greenfield fantasy.

> The ratchet *mechanics* (the `baselines.json` format, the monotonic guard, the anti-gaming rules) are canonical in [engineering-gates.md](../../../../docs/knowledge/engineering-gates.md) §1. This file is the operational layer: which metrics to track, why these and not others, and how to run the ratchet during a convergence pass. It travels with the skill so the skill works in repos that don't have engineering-gates.md.

## The minimal metric set

Pick a small, hard-to-game, research-backed set. Each is enforced as a **monotonically-tightening fitness function**: a committed baseline, a CI failure on regression, an auto-lower on improvement.

| Metric | What it captures | Why it's in the set |
|---|---|---|
| **Cognitive complexity per function** (count over threshold) | human reading effort | The single best readability metric. Penalizes *nesting* and *mixed boolean logic* — exactly what hurts readers. Far better than cyclomatic, which treats a flat 10-arm switch the same as deep nesting and is mostly a proxy for line count. |
| **Duplication %** | copy-paste and re-implementation | Objective, directly actionable, weighted in both CodeScene and SonarSource composites. The metric AI assistants make worse fastest. |
| **Dependency cycles** (target 0) | architectural tangle | Binary; zero-tolerance ratchets cleanly. Cycles block layering and make every nearby refactor ambiguous. |
| **Suppression counts** (`# type: ignore`, `# noqa`, `#[allow]`, `@ts-expect-error`, `except Exception`, `dict[str, Any]`, `cast`, skipped tests) | deferred decisions | Each is a debt with a shelf life. Counting them keeps the cost visible; the net-≤0-per-family rule keeps them from migrating. |
| **Refactored-vs-added ratio** | consolidation vs accretion | Lines moved/consolidated ÷ lines added. The **de-slop north star**: GitClear's data shows "moved" (refactored) code collapsed from ~24% to ~9.5% of changes since AI assistants arrived while copy-paste rose. A healthy convergence pass pushes this ratio *up*. |
| **LOC** (honest proxy only) | bulk | Tracked and celebrated when it falls via *real* consolidation. Never a target on its own — see "Goodhart" below. |

### Why these and not the popular ones

- **Cyclomatic complexity** — keep a per-function ceiling if it's free, but it's largely a line-count proxy and rates flat switches like deep nesting. Cognitive complexity is the one to lean on.
- **Maintainability Index** — avoid as a target. It's dominated by LOC (so splitting a clear file *lowers* its score), averages away the catastrophic-function tail, and its coefficients were calibrated on 1990s C. Report it for humans if you like; never ratchet on it.
- **Raw LOC as a goal** — punishing it rewards dense unreadable code; rewarding it rewards bloat. Proxy only.

## Ranking: churn × complexity

Don't try to fix everything. The cost of low-quality code concentrates in **hotspots** — code that is *both* complex *and* frequently changed (CodeScene's *Code Red* study: low-health code carries ~15× the defects and ~2× the time-in-development, and the cost lives in the hotspots). Complexity in code nobody touches is nearly free.

```
churn   = commits touching the file in the window (git log --format= --name-only <since> | sort | uniq -c | sort -rn)
hotspot = churn × complexity_metric
```

Rank candidate moves by the hotspot score of the code they touch. This is the prioritization engine for Phase 3.

## The ratchet, operationally

Two complementary gates — use both:

1. **Diff-boundary gate (primary).** Enforce the strict standard on *new and changed* code only ("clean as you code"). You never have to enumerate legacy debt; you gate the delta. This is the most practical ratchet and the one to reach for first.
2. **Fingerprinted count baseline (fallback).** For whole-file/whole-repo metrics, store a baseline of counts (or violation fingerprints — hash of file+rule+context, which survives code movement better than raw line numbers). Fail CI on any increase; **auto-regenerate downward** on any improvement so a fixed violation is locked in and the build can never silently regress.

During a convergence pass: after each move improves a metric, run the auto-lower step (Phase 5) immediately, in the same commit as the change that justified it. Promote a gate from advisory to blocking only after it's been stable for a cycle.

## Anti-gaming (each was a real exploit)

- **No metric gaming.** Stripping comments/blanks to slip under a line ceiling is forbidden; `dict[str, Any]` → `dict[str, object]` is the same surrender disguised ("type laundering"). At floor, do the real refactor or change the *formula* — never the number.
- **`headroom 0` is borrowed credit.** Never compress unrelated code to make room for an addition; never land a file at exact-fit (its ceiling becomes its own line count, trapping the next edit).
- **Net-≤0 per suppression family.** A `+1` in one family is paid by a `≥1` reduction in the *same* family in the *same* commit. Switching families to dodge a ratchet trips the sibling ceiling.
- **Stop-the-line.** About to add a suppression → stop, present alternatives (fix it / refactor the call site / surface for review). Adding it as the first move *is* the regression.

## False-positive discipline (or the tool gets switched off)

Google's Tricorder learned this the hard way: a static-analysis tool that nags on noise gets disabled, and then it protects nothing.

- **Surface findings in the workflow** (the diff, the report, the commit), not in a separate dashboard nobody opens.
- **Track the fix/dismiss ratio.** If a check's findings are mostly dismissed, the check is wrong — tighten it or drop it. A convergence tool that proposes spurious refactors loses the user's trust faster than one that finds fewer, real ones.
- **No flag-the-world.** New checks apply going forward (the diff-boundary gate); never dump the entire backlog on the user at once.

## Goodhart's law

Every ratcheted metric is, by definition, a target — and "when a measure becomes a target, it ceases to be a good measure." Design against it: prefer a *small set of hard-to-fake sub-metrics* and the diff-boundary gate over a single optimizable composite. Report a composite "health score" for humans if it helps motivation, but **ratchet on the individual sub-metrics**, never on the composite — composites are the easiest thing to game.
