# Engineering Gates — enforcing code health mechanically

> The *how* behind [engineering-philosophy.md](../engineering-philosophy.md). The philosophy says "if you cannot enforce it, do not claim it." This is the enforcement layer: the concrete gate mechanics that make code-health a floor that only rises. Adopt incrementally; none of it is mandatory.

Guiding idea: **gate the delta, not the backlog.** Grandfather existing debt, block regressions, ratchet the ceiling down over time. This is what makes discipline adoptable on a real codebase instead of a greenfield fantasy.

## 1. The baselines ratchet

A single `baselines.json` records a **ceiling** for every health metric: per-file and per-extension line ceilings, and **counts** of escape hatches — `# type: ignore`, `# noqa`, `#[allow(...)]`, `@ts-expect-error`, `except Exception`, `dict[str, Any]`, `cast(...)`, skipped tests, bare TODOs, `#[cfg(test)]`-in-src. A gate fails any commit where `actual > ceiling`.

The non-obvious half is the **monotonic guard**: a second gate enforces that a ceiling can only ever move **down**. Without it the ratchet is social-only — an agent edits `27 → 28` and CI goes green. Raising a ceiling requires an explicit, auditable commit-message trailer (e.g. `Ratchet-Bump:`) plus an approval marker, checked at the `commit-msg` hook where the message actually exists. Legitimate bumps pass non-interactively but leave a trail; silent regression is impossible. A weekly `auto-ratchet` pass tightens every ceiling to current state (never raises), locking in improvements.

**Anti-gaming rules** (each was a real exploit):
- **No metric gaming.** Mechanically compressing a file (stripping comments/blanks) to slip under a line ceiling is forbidden — a clean, well-organized file beats a mangled one that's nominally shorter. `dict[str, Any]` → `dict[str, object]` is "type laundering," the same surrender disguised. When a metric is at floor, either do the real refactor or change the *formula* — never game the number. LOC is a proxy, not a target.
- **`headroom 0` is borrowed credit.** Never compress *unrelated* existing code to make room for your addition; it hides growth and burns the next agent. Never land a new file at exact-fit (its ceiling becomes its own line count, trapping the next edit) — leave a few lines of slack.
- **Net-≤0 per suppression family.** A `+1` in one family must be paid by a `≥1` reduction in the *same* family in the *same* commit. Switching families to dodge a ratchet trips the sibling ceiling.
- **Stop-the-line.** About to type any suppression marker → stop, present alternatives (fix it / refactor the call site / surface for review). Adding it as the first move is the regression.

## 2. No competing versions

One implementation per concept. When a new version replaces an old one, **delete the old and give the new one the unversioned name, in the same change.** No `FooV2` beside `Foo`, no `transcript_v2` column beside `transcript`, no backward-compat re-export shim. A policy script scans staged additions for versioned identifiers (`*V[1-9]`, `*Legacy`, `*Deprecated`, `*_v[1-9]`) and fails the commit. Allowed: external-protocol versions (`api_version`, `/api/v1/`), frozen migration baselines, and `New` meaning "newly added" (only flagged when paired with `*Old`/`*V1`). Parallel versions require explicit authorization plus a roadmap entry naming the collapse date.

Generalized smell: **whenever you catch yourself proposing "we'll also maintain X alongside Y," stop.** Parallel artifacts drift. The same instinct rejects "keep two baselines" and "build a separate manifest of contract surfaces" — the answer lives inline with the code or in one canonical place generated from a single source of truth.

## 3. CI calls task-runner recipes; YAML holds zero logic

Every CI step is `run: just ci <group>`. No test/lint logic lives in the workflow YAML. One definition, three consumers: **CI, git hooks, and humans** all call the same recipes. This makes "reproduce CI locally" trivially true.

- A `preflight` recipe mirrors the CI workflow job-for-job so you can prove a push lands green before burning CI minutes; a `preflight-fast` variant skips the slow DB/paid/browser lanes with documented rationale for what each skips.
- **Hermetic recipes:** CI/test recipes set `dotenv-load := false` so dev `.env` secrets can't silently contaminate mocked unit tests.
- Organize `just` into `mod` submodules (`just/ci/`, `just/test/`, `just/audit/`, `just/secrets/`) so each concern is browsable via `just <group>`.

## 4. Affectedness-based test selection

One `.affected.yml` maps path globs → `{stacks, scopes, risk: low|medium|high}`. A single script reads it and emits what changed; the **same manifest** drives CI path-filters, the pre-push hook, and local `just test auto`. Risk tiers encode blast radius (a core/shared module = `high` = fan out to the full suite; a leaf module = `low` = scope-only).

- **Map both source AND test paths.** A test-only PR whose globs match nothing resolves to "not affected" and *silently skips its own tests* — a correctness bug, not an optimization.
- **Reject test-impact caches at small scale.** A suite that runs in ~10s under `pytest -n auto --dist loadfile` gains nothing from a selection cache and pays for it in deletion friction and a fragile parallel-worker integration. Use git-diff scoping instead; revisit only when the full suite exceeds ~60s *and* scoping misclassifies *and* it actually hurts.

## 5. Coverage & complexity as ratcheting floors

Set each floor a few points **below** current actual, then ratchet up in steps, each step landed in the same commit as the tests that justify it. Promote a gate **advisory → blocking** only after a stability cycle.

- Coverage: `pytest --cov-fail-under`, `vitest --coverage` line floor, `cargo llvm-cov --fail-under-lines`.
- Complexity: `complexipy -mx N` (Python cognitive), `clippy.toml` `cognitive-complexity-threshold` calibrated just above the current worst offender (ratchet down as offenders are decomposed), CRAP-score gates on the web diff.
- Coverage exclusions (generated/CLI-shell files) live in one shared ignore regex with per-file justifications, never scattered `# pragma: no cover`.

## 6. Contract codegen with a freshness gate

For cross-language contracts, derive from **one** source of truth (e.g. Rust `schemars` → JSON Schema → TS Zod) and gate freshness: CI regenerates and fails if the output diffs. This kills hand-maintained parallel schemas and the silent drift between them.

A related data-integrity hazard: **"default-on-missing" silently absorbs contract drift across a language boundary.** A dropped column that a Pydantic/serde model defaults to `0` can make a downstream filter discard everything, with no error anywhere. Prefer fail-fast on missing required fields, or cover the wire struct with a contract test.

## 7. A required aggregating gate that tolerates skips

With path-filtered CI, branch protection's "required check" can never run on a skipped path → PRs get stuck forever. The fix: one `gate` job that `needs:` every stack job, evaluates each `needs.<job>.result`, and tolerates `skipped` for jobs that legitimately don't run. Branch protection requires only that aggregating gate, so a docs-only change still reports an honest green.

## 8. Cost-aware test taxonomy

Tier verification by execution cost and place each tier where its cost belongs:

| Tier | Cost | Where it runs |
|------|------|---------------|
| static (no execution) | free | hooks + CI, blocking |
| unit (deterministic) | free | hooks + CI, blocking |
| contract (service-boundary) | free | CI, blocking |
| journey (cross-boundary smoke) | free | CI, blocking |
| quality (output meets a rubric) | ~cents per run | manual / nightly |
| model (real-model behavior) | real $ | manual / release only |

**Anti-cheat discipline:** never silence a test without a tracking reason + an offsetting test + a PR note; a pre-push guard refuses net test-line *deletion*; regenerating a snapshot without reading the diff is rubber-stamping (>50 changed lines is a regression until proven otherwise); TODOs carry an owner/date (`# TODO(2026-Q3 or @owner): …`) enforced by a ratchet.

## 9. Hook-failure triage (when a gate blocks you)

- **Preflight all gates upfront** (`just preflight-fast`) before pushing — gates are independent, so discovering them one-at-a-time burns a commit→push→fix round-trip each.
- **Name the failing recipe before fixing.** Most wasted cycles come from retrying blind after misreading which sibling recipe failed. Find the exact recipe, read *that* output only, state "recipe X failed: specific check," then fix.
- **After an amend/rebase, verify HEAD's tree before pushing** — autostash and amend can silently strip a fix or rewrite the wrong commit.
- **"Cache eraser" anti-pattern:** if your recovery is repeatedly `rm -rf <cache>`, the tool isn't a fit — find its documented correct usage and make it permanent, or replace it.
- Never bypass with `--no-verify`.

## See also

- [../engineering-philosophy.md](../engineering-philosophy.md) — the 12 principles each of these gates enforces
- [../stacks/security.md](../stacks/security.md) — the supply-chain & secrets gates
- [../stacks/infrastructure.md](../stacks/infrastructure.md) — CI/CD structure, build discipline
