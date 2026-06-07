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

## Starting a new scope / repo (the adopt path)

One command bootstraps the backbone in any git repo:

```
cd <target-repo>
dotfiles agent health --scope <name> --glob '<files_glob>' --run-from '<dir>'
```

It runs the scorecard against the current repo, seeds `docs/health/<scope>/baselines.json`
(ceilings set to current actuals via `ratchet-check.sh --update`), and seeds a
`findings.md` ledger — then points you at `/converge` to grade and populate the
backlog. Idempotent: re-running keeps existing baselines unless `--force`. Commit
the `docs/health/` it produces so that repo gets the same durable memory.

## Routines — what makes it self-managing

The system converges on its own through three wired routines, not ad-hoc passes.
The dividing line is **schedule the *finding*, gate the *fixing*** — generative
refactoring is never auto-applied (see the [portfolio scheduling
policy](../knowledge/code-health-portfolio.md#scheduling-policy)).

1. **The ratchet gate (enforced every commit).** `just ratchet` runs
   `ratchet-check.sh` against `cli/`'s baseline; it's wired into `just check`, which
   lefthook runs at pre-commit (`--fast`) and pre-push. Any new suppression above a
   ceiling fails the commit. `just ratchet --update` lowers ceilings to current
   actuals (monotonic — never raises), locking in every improvement. This is the
   floor that only rises.
2. **The adopt command (one-shot, deterministic).** `dotfiles agent health` above —
   replicable in any repo with zero re-specification.
3. **Scheduled detection (safe unattended).** `scorecard.sh --json` (diff against the
   committed baseline) and the `ai/audits/*` prompts are safe to run on a cron: they
   **open an issue or draft PR, never auto-merge and never auto-apply a generative
   refactor** — the empirically-documented anti-pattern. Every taste/structural lens
   and all of Tier B stay interactive and human-gated.

### Gotchas the grep-based ratchet has (learned by dogfooding)

- **Pathspec `**` skips shallow files.** A plain `src/**/*.py` git pathspec silently
  omits files directly under `src/`. `ratchet-check.sh` wraps the glob in `:(glob)`
  magic so `**` spans directories *and* matches shallow files.
- **A pattern catalog can match its own grep.** The file that *defines* the
  suppression regexes (`cmd/agent/health.py`) must not contain a family's literal
  match form; factor alternations into groups (`except (Exception|BaseException)`,
  not `except Exception|except BaseException`) so the catalog doesn't self-count.
