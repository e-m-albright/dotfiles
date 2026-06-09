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
- **Stop-the-line.** About to type any suppression marker → stop, present alternatives (fix the underlying issue / refactor the call site / **change the boundary forcing the type confusion** — parse into a typed model at the edge instead of casting downstream / surface for review). Adding it as the first move is the regression.

**The full marker set (if you're about to type ANY of these, stop):** Python — `# noqa`, `# type: ignore`, `# pyright: ignore`, `# pragma: no cover`; Rust — `#[allow(...)]` (every family), `transmute`, `unchecked` unwraps; TS/Svelte — `@ts-ignore`, `@ts-expect-error`, `@ts-nocheck`, `eslint-disable`, `biome-ignore`, `svelte-ignore`, unchecked `as`; tests — `@pytest.mark.skip`, `it.skip`/`describe.skip`, `#[ignore]`; casts — `cast(...)`, `as`, `Box<dyn Any>`. A ratchet that counts only some families just pushes the surrender into an uncounted one (`dict[str, Any]` → `dict[str, object]`, `any` → `unknown`, `Box<dyn Any>` → `Box<dyn Debug>` are all type laundering). Cover every variant or none.

**Every kept suppression carries a `reason:`.** If one genuinely survives review, it gets a same-line, specific, attributable annotation — `# type: ignore[arg-type]  # reason: upstream stub wrong, tracked in <ref>` (Rust: a `// reason:` line above the attribute). "Specific, attributable, dated" — a bare suppression with no reason is itself a regression, independent of the count.

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
- Coverage exclusions (generated/CLI-shell files) live in one shared ignore regex with per-file justifications, never scattered `# pragma: no cover`. When a single branch is hard to cover, **decompose the untested branch into a unit-testable function** rather than dodging the floor with a `no cover` pragma.
- **Performance budgets** are a ratcheting floor too — the Performance pillar's convergent home. `perf-check.sh <perf-baselines.json>` benchmarks each command (hyperfine) and fails past `baseline_ms × (1 + tolerance_pct)`; `--update` lowers baselines to current means, so speedups lock in and a deliberate regression needs a justified bump. Two differences from the static ratchet, both forced by runtime noise: it gates on a **tolerance band**, not an exact ceiling, and it lives at **CI/nightly, not pre-commit** (benchmarks are slow and environment-specific — re-baseline per runner). `just perf` in this repo.

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

## 10. Secrets & supply-chain gates

Secrets never live in files: `.env` holds non-secret local config; real secrets are overlaid at runtime from a manager; `.env.example` is names-only — so "did we leak?" is a structural non-question. Enforce:

- **gitleaks at pre-commit AND CI** (`fetch-depth: 0` so history is scanned), with the **action version pinned** — stock/unpinned versions silently ignore your `[[allowlists]]`. Allowlist surgically: path glob + content regex + a written reason.
- **Pin third-party Actions by commit SHA, not tag.** Tags get force-pushed to malware (the trivy-action compromise, Mar 2026). Treat transport/security-default dependency bumps as manual review, not auto-merge.
- **One `audit-<lang>` recipe per stack** (`pip-audit`, `cargo audit`, `bun audit`…), run on lockfile change; pinned ignores each carry a removal condition.
- **Provisioning ≠ rotation.** A brand-new auth path has no hot fallback, so it gates on a mint→stage→verify→smoke checklist, not merely on merge.

Full detail: [../stacks/security.md](../stacks/security.md).

## 11. Fleet uniformity: one source, translated, drift-gated

§6 generalized from cross-language *code* to cross-target *config/policy*. When a concern is necessarily expressed in N places (per-vendor agent configs, per-language contracts), keep **one authored source plus a test that fails if any target drifts** — never N hand-maintained copies. Example: `ai/agents/shared/deny-commands.yaml` is the source; `test_deny_commands_sync.py` asserts every deny string appears in each vendor's committed config. The instinct is the same as §2: the moment you catch yourself "also maintaining X alongside Y," the answer is a generator or a drift test, not trust. Full: [agent-fleet.md](agent-fleet.md).

## 12. Reproducible, hermetic builds

CI and local must agree bit-for-bit, and a build must not depend on ambient state.

- **Pin toolchains exactly** (language version, action SHAs) so CI and the local agent run identical tools.
- **Hermetic recipes:** `dotenv-load := false` on CI/test recipes so dev `.env` can't contaminate mocked tests; build against committed offline artifacts (e.g. `SQLX_OFFLINE=true` + a committed `.sqlx/`).
- **Applied migrations are immutable** — checksum-locked, never edited; a change is always a *new* migration, never an edit to a shipped one.
- **Change-detection deploys** (skip a service whose source didn't change) and **health-gated ordering** (deploy a dependency → wait healthy → start its clients).

Full: [../stacks/infrastructure.md](../stacks/infrastructure.md).

## 13. Fail loud, never silent in your own layer

The recurring meta-hazard behind §6's "default-on-missing absorbs contract drift": a component that swallows a fault in the layer it lives in fails *invisibly*, and the symptom surfaces somewhere unrelated. Same class, different layers: a Pydantic/serde model defaulting a dropped column to `0` (data); a blocking telemetry exporter starving the event loop until liveness 503s every caller (runtime); OTLP metadata keys that must be lowercase or are silently dropped, taking observability dark (transport). Prefer fail-fast on missing required input, and make every swallowed error an event (philosophy §7, §9). Runtime catalog: [../stacks/infrastructure.md](../stacks/infrastructure.md).

## 14. Refactoring & deploy safety

Hard-won traps from large agentic refactors. Most are judgment, not gates, so they live here as discipline — and saying so is the point ("if you cannot enforce it cleanly, don't fake a noisy gate"):

- **Never blanket find/replace a token that can appear in prose, URLs, or example paths.** A bare `sed 's/old/new/'` corrupts links and docs (and BSD `sed` silently no-ops some patterns). Replace only the backtick / slash / identifier forms, then diff and link-check the change by hand. A *repo-wide* link gate is noise — illustrative `foo.md` / `./src/...` example paths dominate the false positives — so verify the **delta**, not the backlog.
- **A rename leaves orphaned deployed artifacts.** `npx skills add --copy` skips existing dirs and never prunes old names; after a rename you must `npx skills remove <oldnames>` per vendor, then redeploy. Deploy tooling prunes by *current source names only* — deliberately, so it can't nuke externally-installed skills — so orphan cleanup on a rename is a manual step.
- **Malformed frontmatter deploys as *nothing*** — the one that IS gated. `npx skills` silently drops a skill whose YAML is invalid, so a typo'd skill deploys as simply gone. `just lint-agents` (`dotfiles agent lint`) at pre-commit + CI catches it before deploy.
- **Arbitrate audit findings; don't mass-execute.** Scheduled/audit output is a worklist to triage, not a script to run — *schedule the finding, gate the fixing*.
- **Stage only your own paths.** When an owner edits in parallel, `git add <explicit paths>` — never `git add -A`, which sweeps their untracked work into your commit.

## See also

- [../engineering-philosophy.md](../engineering-philosophy.md) — the 12 principles each of these gates enforces
- [../../CANON.md](../../CANON.md) — these gates are the enforcement articles of the Canon (§III)
- [how-we-build.md](how-we-build.md) — where each gate fires in the defense-in-depth ladder
