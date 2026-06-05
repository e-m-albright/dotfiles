# De-slop

Stripping AI bloat and shallow complexity: the smell catalog to detect, the transforms to reduce conditional bloat, and the pipeline to find "this re-implements that." Also serves as the self-contained diagnostic brief for Phase 2 in repos without `ai/audits/`.

**Why this matters, with numbers.** GitClear's analysis of 211M changed lines (2020–2024) found duplicated code *blocks* rose ~8× by 2024, copy/paste share of lines rose ~48%, and "moved" (genuinely refactored/consolidated) code collapsed from ~24% to ~9.5% — i.e. AI assistants *add* rather than consolidate. CodeRabbit's PR study found AI-co-authored PRs carry ~1.7× the issues, with readability ~3× and over-defensive/perf regressions much higher. The signal is consistent across independent sources (treat exact multipliers as indicative, not gospel): **AI-assisted code trends toward bulk, duplication, and defensive noise.** De-slopping inverts that trend.

## The AI-slop catalog

What to look for. Each is a candidate move; classify and propose the fix.

1. **Speculative / premature abstraction** — an interface, factory, config knob, or generic for a need that doesn't exist. Builds a framework for a 10-line problem. *Fix:* inline it; honor the rule of three. (Wrong/premature abstraction — see "Abstractions" below.)
2. **Defensive over-programming** — try/catch around code that can't throw, null/guard checks the types already guarantee, re-validating trusted internal data, over-logging. *Fix:* delete the checks the type system makes impossible; validate once at the boundary, trust types inside.
3. **Cargo-cult code** — retry logic where nothing fails, error handling that swallows everything, patterns copied without their reason. *Fix:* remove or make the reason explicit.
4. **Duplicated helpers instead of reuse** — re-implements a function that already exists because the model didn't find it. The GitClear 8× signal. *Fix:* replace with a call to the canonical home (see semantic-dedup pipeline).
5. **Convention-blindness** — generic "good code" that ignores the repo's naming, layout, and idioms. Technically fine, wrong for this system. *Fix:* conform to the ontology and the local stack taste.
6. **Verbose boilerplate & over-commenting** — comments restating the code, ceremony that adds no behavior. *Fix:* delete comments that narrate the obvious; keep only the *why*.
7. **Complexity inflation** — higher cognitive complexity than the task warrants; nested conditionals where a guard clause or lookup would do. *Fix:* the conditional transforms below.
8. **Leaked external shapes** — an API's field names used as domain vocabulary inside the core. *Fix:* map to the ubiquitous language at the boundary (anti-corruption).
9. **End-to-end-only testability** — logic entangled with effects so it can only be tested through the whole stack. *Fix:* extract a pure core (humble object), leave a thin adapter.
10. **Plausible-but-wrong / API hallucination** — calls to non-existent or deprecated APIs, edge-case-wrong logic. (This shades into bug territory — hand correctness defects to `/review`.)

A useful composite "slop score" per file: semantic-duplication ratio + churn/revert rate + complexity-over-budget + convention divergence + (test *behavior* coverage, inverted).

## God functions & data clumps (Phase 2 brief)

- **God function** — can't describe the job without "and"; >5 params; >3 nesting levels in business logic; mixes I/O with computation. *Fix:* name the seams the "and"s reveal, extract them. Verify the extraction reduces the function's complexity, not just its line count.
- **Data clump** — 3+ values always initialized/passed/returned together. *Fix:* name the missing struct/dataclass/model and replace the loose primitives with it.

## Abstractions (Phase 2 brief)

Classify each finding:
- **Missing** — 2+ near-identical implementations, repeated patterns, casts/`Any`/ignores at a boundary that a type would remove. *Fix:* extract — but only at the rule of three and only if the shape is stable.
- **Premature** — one concrete caller, never-varied config, a base class with one subclass. *Fix:* inline it.
- **Wrong-level** — one function mixing HTTP + business logic + DB. *Fix:* split by layer.
- **Wrong abstraction** — an over-parameterized shared thing every caller bends around. *Fix:* re-inline into each caller, delete the params each doesn't need, let the duplication show the right seam (Metz). Re-inlining is progress, not waste.
- **Semantic duplicate** — two modules solving the same problem differently; parallel registries. *Fix:* pick one canonical home, migrate, delete the other (no competing versions).

## Reducing conditional bloat

The metric to move is **cognitive complexity** (nesting-weighted), not cyclomatic. A refactor that flattens nesting can leave cyclomatic unchanged while dropping cognitive complexity sharply — and that's the one readers feel.

The transforms (Fowler's catalog), with a selection heuristic:

| You see… | Apply | Result |
|---|---|---|
| Deep nesting with early-exit structure | **Replace nested conditional with guard clauses** | `if (bad) return; … happy path at top level`. The highest-value de-nesting move. |
| Dispatch on a **value/key** (long if/elif or switch on a string/enum) | **Replace conditional with lookup map / table-driven dispatch** | a dict/table keyed on the value; the chain disappears. |
| Dispatch on a **type/variant** | **Replace conditional with polymorphism / strategy** | each variant owns its method; the switch vanishes. |
| A complex boolean buried inline | **Decompose conditional** | extract condition and branches into named functions (`isEligible()`, `applyDiscount()`). |
| Several conditionals with the **same result** | **Consolidate conditional expression** | merge into one combined expression, then extract it. |
| A boolean flag steering a loop/flow | **Replace control flag with break/return** | remove the flag; exit directly. |

Heuristic in one line: **value → lookup table; type → polymorphism; nesting → guard clauses; tangled boolean → decompose/consolidate then extract.**

These are behavior-preserving and largely mechanical — good candidates for auto-fix and for deterministic codemods (ast-grep / OpenRewrite / comby) where the pattern is regular.

## The semantic-dedup pipeline

Token-based clone detectors (`jscpd`, PMD CPD, Simian) catch only Type-1/2 clones (identical or renamed). They miss exactly the "this re-implements that" duplication AI produces (Type-3: edited; Type-4: same behavior, different code). Layer the detection so each stage is cheap before the expensive one:

1. **Token sweep** — `jscpd` / PMD CPD for a fast Type-1/2 pass. Cheap, high precision.
2. **Embedding retrieval** — embed functions and retrieve near-neighbors as Type-3/4 *candidates*. Narrows the field.
3. **Confirm** — read the candidate pair and judge functional equivalence; where stakes are high, confirm by running the suite (or shared inputs) against both. Only then propose "replace this re-implementation with a call to canonical X."

Never auto-merge on a similarity score alone — a confident-but-wrong dedup couples two things that only *looked* alike. Dedup is a *suggested, reversible* move; confirm equivalence first, and route the actual merge through a normal verified Phase-4 step.

## Deterministic tools vs your judgment

Route the **mechanical, behavior-preserving bulk** through codemods — they're correct by construction and don't burn context:

- **ast-grep** — polyglot (JS/TS, Python, Go, Rust, …), tree-sitter rules, fast. The default for structural find-rewrite.
- **OpenRewrite / Moderne** — JVM-first, type-aware Lossless Semantic Tree; best for systematic, repeatable migrations.
- **comby** — lightweight structural search-replace across many languages.
- **jscodeshift** — the JS/TS ecosystem standard.
- **Semgrep `--autofix`** — rule-driven mechanical fixes, security-aware.

Reserve your own reasoning for what a codemod *can't* express: which abstraction to extract, what to name it, whether two functions are *really* the same, and every judgment call. The winning shape is **LLM proposes the plan and the edit intent → deterministic tool executes the transform → the test suite verifies.**
