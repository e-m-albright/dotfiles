# Defense in Depth — the Layers (L0–L5) in Detail

> The **Defense-in-depth** column of the [Engineering Map](../../ENGINEERING.md), zoomed in.
> The map gives the one-screen nesting (doctrine → enforcement → layers → tools) and the IDs;
> this page is the deep dive on *where and when* each gate fires — layered cheapest-first, so
> quality is **enforced in depth** rather than hoped for. Generic by design; a project tweaks
> the specifics, never the shape.

The thesis in one line: **catch each class of defect at the cheapest layer that can catch it, make every stochastic gain durable by recording it as a deterministic floor, and let nothing that can be enforced survive as mere prose.**

---

## The one-screen map

```
                         ┌──────────────────────────────────────────────┐
                         │                 THE  CANON                    │
                         │     what is true — the doctrine you don't     │
                         │            relitigate every PR                │
                         │   kernel articles · 12 principles · toolbelt  │
                         │        doctrine · evidence · arbitrations     │
                         └───────────────────────┬──────────────────────┘
                            every gate below enacts an article ▼

   THE  CATECHISM  —  defense in depth, cheapest layer first  (← shift left)
   ════════════════════════════════════════════════════════════════════════
                                                              D = deterministic
   L0  AUTHOR-TIME      types · LSP · compiler-as-first-reviewer    S = stochastic
   ░░░░░░░░░░░░░░       AI pair: rules + skills (form lenses,        (LLM judgment)
       │                planning, TDD, design) invoked on demand        [D + S]
       ▼
   L1  PRE-COMMIT       just check --fast  ·  lefthook, changed files only   [D]
   ▓▓▓▓▓▓▓▓▓▓▓▓         fmt → lint → types → deadcode → complexity → RATCHET
       │
       ▼
   L2  PRE-PUSH         just check   (everything above + tests, coverage ≥ 85) [D]
   ▓▓▓▓▓▓▓▓▓▓▓▓
       │
       ▼
   L3  CI               just check (identical recipes) · shell/json/yaml ·    [D]
   ▓▓▓▓▓▓▓▓▓▓▓▓         secrets scan · aggregating gate that tolerates skips
       │                "CI calls recipes; YAML holds zero logic"
       ▼
   L4  SCHEDULED        scorecard (D) + audit skills (S) → issue / draft PR   [D + S]
   ▒▒▒▒▒▒▒▒▒▒▒▒         never auto-merge.  "schedule the finding, gate the fixing"
       │
       ▼
   L5  CONVERGENCE      the `converge` engine, on demand:                  [S → D]
   ▒▒▒▒▒▒▒▒▒▒▒▒         measure → systematic-debugging → refactor → LOWER THE BASELINES
                        purifies existing code; ratchets the win in

   ════════════════════════════════════════════════════════════════════════
   THE RATCHET runs at L1 · L2 · L3 — the floor that only rises.  ▓ = blocking
   It is the BRIDGE: a stochastic gain at L0/L5 becomes a deterministic floor here.
```

**Two readings of the same picture:**

1. **Shift-left (vertical).** A defect is cheapest to kill where it's born. A type error dies in the editor (L0); a style drift dies at pre-commit (L1); a broken test dies at pre-push (L2); a contributor-without-hooks is caught by CI (L3); slow-accruing rot is *found* by schedule (L4) and *fixed* by convergence (L5). Each layer is the safety net for the one above it.
2. **Deterministic spine, stochastic leaves (the shading).** The **floor** (▓ L1–L3, the ratchet, the permission substrate) is entirely deterministic — linters, types, counts, coverage. The **judgment** (░▒ L0, L4, L5 — the lenses, audits, reviews) is stochastic LLM work. They meet at the ratchet, which is the only thing that can make taste *stick*.

---

## The layers in detail

Each rite is tagged **[D]** deterministic or **[S]** stochastic and linked to the Canon article it enacts (P# = one of the [12 principles](../engineering-philosophy.md); K = the [kernel](../../ai/agents/shared/rules.md)).

### L0 · Author-time — while you write
The cheapest layer: the invariant never enters the tree.
- **Types / compiler / LSP** [D] — every statically-checkable invariant is checked in the editor. *P1 the compiler is the first reviewer; P2 type the domain.*
- **The AI pair** [S] — rules + skills loaded into Claude Code / Cursor / Codex. The author reaches for a rite via the **Catechism** (`dotfiles agent catechism`):
  - *form lenses* — `form-deepen`, `form-tidy`, `form-prune`, `form-clarify`, `form-align`, `form-purify` (behavior-preserving), routed by `code-health`.
  - *pre-code judgment* — `planning`, `collaborative-ideation`, `grill-with-docs`, `prototype`.
  - *TDD* — `test-driven-development` (write the test first; deep modules). *P11.*
  - *frontend* — `impeccable`, `design-review`, `browser-tooling`.

### L1 · Pre-commit — `just check --fast` (lefthook, staged files only) [all D]
`fmt --check` → `lint` (ruff) → `types` (pyright) → `deadcode` (vulture) → `complexity` (complexipy `-mx 9`) → **`ratchet`**. Plus per-type validity: `shellcheck`, `bash -n`, `yq`, `jq`. *P1, P5, P6, P10.* Fast, parallel, never `--no-verify`.

### L2 · Pre-push — `just check` [all D]
Everything in `--fast` **plus** `test` (pytest, `--cov-fail-under=85`). The last gate before the network. *P11.*

### L3 · CI — `.github/workflows/ci.yml` [all D]
The `cli` job is literally `just check` — **the same recipes hooks run locally**, so "reproduce CI" is trivially true and a missing-hooks contributor can't bypass the floor. Plus shell/json/yaml validity, a secrets-pattern scan, and (the pattern) an aggregating `gate` job that `needs:` every stack job and **tolerates `skipped`** so a docs-only PR still reports honest green. *Engineering-gates §3, §7.*

### L4 · Scheduled / async — *schedule the finding, gate the fixing*
Runs on a cadence; **opens an issue or draft PR, never auto-merges, never auto-applies a generative refactor** (a cited anti-pattern — unattended refactoring is cosmetic, 53.9% scope-creep).
- **Orchestration** — [`ai/routines/`](../../ai/routines/): `registry.json` (one entry per routine: cron, model, audits, output, optional `stacks` for affectedness) + `protocol.md` (the shared run loop: affectedness-gate → fresh scan branch → run audits/scorecard → synthesize → write `findings.md` → open a draft PR). The only file a routine writes is the ledger.
- `scorecard.sh` [D] — LOC, suppression counts, churn×LOC hotspots; diff against the committed baseline.
- audit skills [S] — the [`ai/audits/`](../../ai/audits/) scanner library: generic (`structural`, `security`, `bug-hunt`, `duplication`, `coupling`, `abstractions`, `ai-usage`, `docs-drift`, `observability`, `god-functions`) + `stacks:`-tagged stack-specific (`rust-contracts`, `python-contracts`, `sql-contracts`, `primitive-obsession`, `sqlx-cache`, `migration-safety`) run only on a matching repo. *P3, P4, P5.*

### L5 · Convergence — the `converge` engine, on demand [S → D]
The loop that purifies *existing* code: **measure** (scorecard) → **diagnose** (rank by churn×complexity) → **refactor** (auto-fix mechanical, grill judgment calls) → **lower the baselines**. The final step is what turns a one-off stochastic improvement into a permanent deterministic floor. Reads/writes the `docs/adr/` rejected-decision log (anti-oscillation memory) and `docs/health/<scope>/` state.

### On-demand review (any time before merge) [S]
`review` (`/review`) fans out correctness/security/data-integrity/ops threads + the health rubric → one verdict + letter grade; `/security-review`; `systematic-debugging` (hard bugs); `performance-engineer` (bottlenecks). These change or judge behavior — they are not refactors (Tier B).

---

## The ratchet — the floor that only rises

The single mechanism that makes the whole thing converge instead of drift. `ratchet-check.sh` against `docs/health/<scope>/baselines.json`, enforced at L1·L2·L3.

- **Gate the delta, not the backlog.** Grandfather existing debt; block regressions; ratchet ceilings *down only*.
- **Monotonic guard.** A ceiling can only move down; raising one needs an auditable `Ratchet-Bump:` trailer + approval. `--update` lowers ceilings to current actuals, locking in every win.
- **What it counts:** per-file line ceilings; per-family suppression counts (`# type: ignore`, `# noqa`, `except Exception`, `dict[str,Any]`, `cast`, skipped tests, TODOs…); cognitive complexity; coverage floor.
- **A perf twin** (`perf-check.sh` / `just perf`): the same lower-only ratchet for runtime budgets, but gating on a **tolerance band** (perf is noisy) and living at **CI/nightly**, not pre-commit. The Performance pillar's convergent home.
- **Anti-gaming** (each was a real exploit): no metric gaming / **type laundering** (`dict[str,Any]`→`dict[str,object]`); **net-≤0 per family** (a +1 paid by a −1 in the *same* family, same commit); `headroom 0` is borrowed credit (never compress unrelated code to fit); cover **every** suppression variant or none; every kept suppression carries a dated `# reason:`.
- **Its own footguns** (dogfooded, [health/README](../health/README.md#gotchas-the-grep-based-ratchet-has-learned-by-dogfooding)): a `**` git pathspec silently skips shallow files (use `:(glob)`); a pattern catalog can match its own grep (factor alternations into groups).

---

## Deterministic vs stochastic — and the bridge

| | Deterministic (the spine) | Stochastic (the leaves) |
|---|---|---|
| **Examples** | types, linters, `bash -n`, the ratchet, coverage floor, complexity ceiling, secrets scan, permission profiles, drift-sync tests | the form lenses, `converge`, the audit skills, `review`, the subagents, LLM-judge evals |
| **Property** | repeatable, cheap, blocking, dumb | judgment, contextual, advisory, expensive |
| **Where** | L1–L3 (+ L9 substrate) | L0, L4, L5, on-demand |
| **Failure mode** | misses semantics (a `# type: ignore` in a string still counts) | non-reproducible (two runs grade differently) |

**The bridge is the ratchet.** A stochastic win (a lens deepens a module, an audit finds slop you delete) is fragile until `converge` records the new actuals as baselines — then it's a deterministic floor the next change can't breach. *Taste, made durable.*

**The canonical illustration is voice** (the kernel's "no slop / calibrate confidence" article): the **phrase blocklist** ("Great question", "it's worth noting", em-dash spam) is deterministic and blocks at commit-msg/pre-commit (`just lint-prose` over `ai/agents/shared/slop-phrases.txt`); **tone and confidence calibration** are irreducibly semantic, so they're the stochastic `ai/audits/voice.md` that only advises. One article, two enforcement classes — the whole map in miniature.

---

## The test pyramid — cost-aware, mapped to layers

Tier verification by execution cost; place each tier where its cost belongs (engineering-gates §8, `testing` skill).

| Tier | D/S | Cost | Gate layer |
|---|---|---|---|
| static (no execution) | D | free | L1 + L3, blocking |
| unit (deterministic) | D | free | L1/L2 + L3, blocking |
| contract (service-boundary) | D | free | L3, blocking |
| journey (cross-boundary smoke) | D | free | L3, blocking |
| quality (output meets a rubric, LLM-judge) | S | ~cents | manual / nightly (L4) |
| model (real-model behavior) | S | real $ | release only (L5/manual) |

Selection is **affectedness-based**: one `.affected.yml` maps path globs → `{stacks, scopes, risk}` and drives CI filters, the pre-push hook, and `just test auto` from one manifest. Anti-cheat: a pre-push guard refuses net test-line deletion; a >50-line snapshot regen is rubber-stamping until proven otherwise. The same cost-tiered logic governs **browser/E2E tooling** (Playwright-in-CI → cheap CLIs → MCPs → Stagehand; pick the cheapest tier that does the job).

---

## The rite index — the full Catechism

Everything we can reach for, grouped. (`dotfiles agent catechism` prints the code-health routing; this is the complete set.)

- **Code-health form lenses** [S] — `code-health` (router) · `converge` (engine) · `form-deepen` `form-tidy` `form-prune` `form-clarify` `code-style` `form-align` `form-purify`.
- **Review / safety / speed (Tier B)** [S] — `review` · `/security-review` · `systematic-debugging` · `performance-engineer`.
- **Audits** [S] — `god-functions` · `duplication` · `coupling` · `abstractions`.
- **Testing** [S] — `testing` (taxonomy) · `test-driven-development` · framework skills (`vitest`, `playwright-e2e-testing`).
- **Planning / ideation** [S] — `planning` · `collaborative-ideation` · `grill-with-docs` · `prototype`.
- **Git / PR workflow** [S] — `github-workflow` · `pr-summary` · `pr-greenlight-cycle` · `hook-failure-triage` · `git-worktree-manager` · `commit-commands:*`.
- **Frontend** [S] — `impeccable` · `design-review` · `browser-tooling` · `agentic-e2e-debugging`.
- **Subagents** [S] — `debugger` · `error-detective` · `performance-engineer` · `security-auditor` · `legacy-modernizer`.
- **Session / infra / meta** [S] — `session-recovery` · `workspace-health-audit` · `workflow-closeout-learning` · `dotfiles-doctor` · `skill-creator` · `find-skills` · `dep-audit` · `migration-writer`. (Agentic-setup snapshots are the `dotfiles agent overview` command, not a skill.)
- **Builders / stack reference** [S] — MCP/Cloudflare builders + per-stack skills (`fastapi`, `axum`, `go-chi-handler`, `sqlc`, `alembic`, `tauri`, `sveltekit-svelte5-tailwind`, …).
- **Tooling (deterministic CLI)** [D] — `dotfiles agent health · catechism · stats · lint · setup · overview · verify` · `dotfiles doctor` · `just ratchet` · `just perf` (perf-budget ratchet).

---

## Cross-cutting doctrines (folded in from the deep docs)

The map would be incomplete without these — each is an enforced "how we build" pattern that lives in a specialist doc:

- **Secrets & supply-chain** → [`docs/stacks/security.md`](../stacks/security.md). Secrets never in files (`.env` = non-secret config; `.env.example` = names only); gitleaks at pre-commit **and** CI; pin third-party Actions by **commit SHA** (tags get force-pushed to malware); provisioning ≠ rotation (new auth paths block on mint→stage→verify→smoke, not on merge).
- **Fleet uniformity** → [`docs/knowledge/agent-fleet.md`](agent-fleet.md). One source of truth per concern, translated per vendor, **drift-gated by a test** (`deny-commands.yaml` + `test_deny_commands_sync.py`). The same "one source, checked outward" article as contract codegen.
- **Reproducible builds** → [`docs/stacks/infrastructure.md`](../stacks/infrastructure.md). CI calls recipes; pin toolchains exactly; applied migrations are immutable + checksum-locked; change-detection deploys; health-gated ordering. Plus the **silent-in-layer failure** family (a blocking exporter starves the event loop; lowercase-only OTLP keys) — the runtime twin of "default-on-missing absorbs contract drift."
- **Memory & decisions** → [`docs/knowledge/project-memory.md`](project-memory.md). Decisions live in the repo, not a tool's private memory: `AGENTS.md` (curated current state) + append-only ADRs (supersede, never edit) + per-scope `docs/health/` state. The ADR is the ratchet for the unmeasurable.
- **Context as a budget** → [`docs/knowledge/token-efficiency.md`](token-efficiency.md). Each instruction line must prevent a concrete mistake; one task per session + `/clear`; route models by task class; defer tool loading. The "how we work" article the kernel implies but doesn't yet gate.
- **Why gates over prose** → [`docs/knowledge/prompting/prompt-tactics.md`](prompting/prompt-tactics.md). ~100 scoped prompt directives produce *worse* code (malicious compliance); fix = fewer broad rules **enforced by linters**. The empirical backing for "if you cannot enforce it, do not claim it."

---

## How to work within it — the daily loop

1. **Open the Catechism.** Unsure what to reach for? `dotfiles agent catechism`, or describe the symptom to `code-health`.
2. **Adopt, once per repo.** `dotfiles agent health` seeds the ratchet + ledger.
3. **Write at L0** with the compiler and the AI pair; reach for a lens when something feels off.
4. **Commit** — L1 runs `just check --fast` automatically. A gate fires? `hook-failure-triage`: preflight all gates, name the failing recipe, fix *that*; never `--no-verify`.
5. **Push** — L2 runs the full `just check`. **Verify locally first** to stop burning CI minutes.
6. **Open a PR** — `pr-summary`; CI (L3) re-runs the identical recipes; `review` before merge.
7. **Let it converge** — L4 detection runs on a cadence and files findings; you (or `converge`) fix them human-gated, and the ratchet locks the win in.

---

## Extending the codex

This map is a living artifact, built on the shoulders of giants (Ousterhout, Fowler/Beck, Evans, Metz, CISQ/ISO 5055, CodeScene, Google's *SE at Google*) and on lessons learned the hard way. To extend it, obey **the binding law**:

> **Every rite traces to an article; every article has a rite.** Adding a practice means naming the article it serves, or it's superstition. Adding an article means naming the rite that will enforce it, or it's a claim we can't keep.

**Known open frontiers** (where the codex should grow next):
- **Voice gates — shipped.** `just lint-prose` (deterministic slop-phrase blocklist, blocking) + an **em-dash advisory** (warn, `.md`-exempt, on code + commit messages — `exit 0` per the fight-loop guardrails, promotable to blocking) + `ai/audits/voice.md` (stochastic). Remaining: a commit-lint for imperative mood.
- **All four CISQ pillars now have a convergent home.** Maintainability (`converge` + the ratchet), Performance (`perf-check.sh` / `just perf`), Reliability (coverage floor + **mutation score** via `just mutation` + silent-catch/skipped ratchets), Security (dep-audit + gitleaks + the suppression ratchet). The remaining work is *operational*, not architectural: **establish perf + mutation baselines and wire them into a nightly CI job** (both are slow/noisy, so they live above L3, not in it).
- **Scheduled detection — orchestration shipped.** [`ai/routines/`](../../ai/routines/) (`registry.json` + `protocol.md`) declares the routines and the detect-only run loop, consuming the `ai/audits/` library + `scorecard.sh`. Remaining: a cron runner to execute the registry (the `schedule` builtin or a CI cron).
- **Fold the siloed doctrines** (security, fleet-uniformity, build-discipline) into the Canon's enforcement articles, not just this map's pointers.
- **Language packs** — the ratchet's suppression catalog is Python/TS/Rust-flavoured; "any repo" is really "any repo we've hand-coded patterns for."

See [`docs/health/ASSESSMENT.md`](../health/ASSESSMENT.md) for the independent critique that names these gaps, and [`ENGINEERING.md`](../../ENGINEERING.md) for the doctrine itself.
