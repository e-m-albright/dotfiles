# Repo Standards — the opt-in baseline every repo should meet

> **Last reviewed**: 2026-06-09 — Refresh when the toolbelt changes (new gate, new ratchet family, a stack convention shifts).

The dotfiles repo configures **agents** globally. This doc is the other half: the **per-repo** baseline a project opts into so any agent (or human) lands in a repo that enforces our quality bar by itself. It is a **checklist, not a scaffolder** — we deliberately don't auto-generate repos (templates rot and fight project-specific choices). Adopt items by hand, cheapest-first; each links to the canonical example in this repo or a skill that sets it up.

The organizing principle is [`how-we-build.md`](how-we-build.md): **catch each class of defect at the cheapest layer that can catch it, and make every stochastic gain a deterministic floor.** A conforming repo has a real artifact at each layer below.

---

## The checklist

Copy this into a tracking issue when bringing a repo up to standard. `[ ]` = not yet · `[~]` = partial · `[x]` = done.

### 1. Context & contract — what the repo *is*
- [ ] **`AGENTS.md`** at root, with `CLAUDE.md` + `GEMINI.md` **symlinked** to it (so every harness loads one hand-authored doc). Contains a `## Project Context` (what/why), key invariants, and command style. Big domain glossary graduates to `DOMAIN.md`.
- [ ] **`README.md`** — user-facing: what it does, install, the few commands that matter. Updated in the *same commit* as any command/config change.
- [ ] **Lean-startup context** — a short, honest statement of the problem, the non-goals, and the current stage (so agents don't gold-plate). One paragraph in AGENTS.md `## Project Context`, not a deck. See the `planning` skill for the should-we-build-this lens.

### 2. Task runner — one obvious entry point
- [ ] **`justfile`** with a `default` recipe that lists recipes, and a **`check`** recipe that runs the full gate (lint + types + tests). CI calls *these recipes* — no logic in YAML. See this repo's `justfile` + the `project-files` skill.
- [ ] **`check --fast`** variant for pre-commit (staged/affected only); full `check` for pre-push/CI.

### 3. Author-time (L0) — invariants that never enter the tree
- [ ] **Formatter + linter** wired into the editor and as a recipe: Python → `ruff`; TS → biome/eslint+prettier; Rust → `rustfmt`+`clippy`; Go → `gofmt`+`golangci-lint`. See `docs/stacks/` for per-language taste.
- [ ] **Type checker** in strict mode where the language has one: `pyright`/`mypy --strict`, `tsc --noEmit`, Rust's own.

### 4. Pre-commit (L1) & pre-push (L2) — `lefthook`
- [ ] **`lefthook.yml`** with `pre-commit` (fast, staged-glob: format-check, lint, syntax/JSON/YAML validity, `check --fast`) and `pre-push` (full `check`). Mirror this repo's `lefthook.yml`.
- [ ] **`lefthook install`** documented in the README/bootstrap so a fresh clone is gated.
- [ ] **Secrets never committed** — a staged-files secret-pattern scan (or `gitleaks`) at pre-commit; `.env` gitignored with a checked-in `.env.example`.

### 5. The ratchet (L1/CI) — make stochastic gains permanent
- [ ] **`docs/health/<scope>/baselines.json`** — the monotonic floor (LOC, complexity ceiling, suppression counts: `type-ignore`/`cast`/`Any`/`noqa`/`broad-except`). Bootstrap with `dotfiles agent health`.
- [ ] **A ratchet check** in the gate that fails on any new suppression above the ceiling (every ceiling may only *decrease*; raising one needs a recorded reason). See the `converge` skill's `ratchet-check.sh`.
- [ ] **(optional) a perf twin** — `perf-check.sh` with a tolerance band at CI/nightly, for repos with runtime budgets.

### 6. CI (L3) — the floor a hooks-less contributor can't bypass
- [ ] **`.github/workflows/ci.yml`** whose job is *literally `just check`* (the same recipes hooks run locally — "reproduce CI" is then trivial).
- [ ] **An aggregating `gate` job** that `needs:` every stack job and **tolerates `skipped`**, so a docs-only PR still reports honest green.
- [ ] Shell/JSON/YAML validity + the secrets scan run in CI too.

### 7. Tests — cost-aware, mapped to layers
- [ ] **A `tests/` layout (or colocated)** with markers for tiers (unit/integration/slow/model), per the `testing` skill. Fast tiers gate pre-push; slow/model tiers gate CI/nightly.
- [ ] **TDD when tests exist** — new logic/bugfixes ship with tests; the gate runs the affected set.

### 8. Scheduled / convergence (L4/L5) — *optional, for maturing repos*
- [ ] **A scheduled audit** (the `bot-audits` pattern) that *opens an issue/draft PR, never auto-merges* — finds slow-accruing rot.
- [ ] **`converge` on demand** to pay down whole-repo debt and ratchet the gains in.

---

## How to use this

1. **Audit by reading**, not tooling — walk the checklist against the repo; mark `[ ]/[~]/[x]`.
2. **Adopt cheapest-first** — L0 (format/lint/types) buys the most per minute; the ratchet locks gains; CI makes them unbypassable.
3. **Don't cargo-cult** — a 200-line script doesn't need a perf twin or scheduled convergence. Match the layer set to the repo's stage (the lean-startup lens).
4. **The canonical reference implementation is this repo** — `lefthook.yml`, `justfile`, `cli/`'s ratchet, `.github/workflows/`, `docs/health/`. When in doubt, copy what's here.

This is doctrine we evolve: when the toolbelt gains a gate, add the checklist item here and bump the review date. The `code-health` Catechism (`dotfiles agent catechism`) is the *intra-repo* backbone; this is the *cross-repo* one.
