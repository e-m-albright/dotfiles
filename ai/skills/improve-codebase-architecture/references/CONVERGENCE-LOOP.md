# The Convergence Loop

The full mechanics of the six phases, the execution discipline that keeps refactors safe, and the conditions that tell you the area has converged. Assumes the vocabulary in [LANGUAGE.md](LANGUAGE.md).

The loop exists to solve one problem: **refactoring that never ends.** A codebase without a named target drifts; each cleanup is undone by the next feature. Convergence means (a) a named steady state, (b) a finite list of moves to reach it, and (c) a ratchet so reached states can't regress. When the move list is empty and the contracts hold, you are done — not "done for now," done.

## Phase 0 — Target

The target is the steady state you are converging toward. Derive it from what exists; don't impose a fantasy architecture.

Four facets:

1. **Ontology** — the ubiquitous language. Module names come from here. Read `CONTEXT.md` / `CONTEXT-MAP.md`, or a `## Domain Language` section in `AGENTS.md`. A bounded-context boundary (where the language changes) is where a top-level package boundary belongs. See [ONTOLOGY-AND-HIERARCHY.md](ONTOLOGY-AND-HIERARCHY.md).
2. **Hierarchy** — the directory tree as a literal index of the domain: package-by-feature, top-level dirs that name the domain not the framework.
3. **Dependency shape** — zero cycles; dependencies point toward stability (the dependency matrix trends lower-triangular).
4. **Depth** — deep modules, errors defined out of existence, idiomatic per language.

Do this as a **top-down pass before any hotspot work**. The Phase-1 churn×complexity ranking is deliberately local and will happily polish modules while the whole package decomposition stays wrong; only a top-down look catches a mis-drawn bounded context or a cross-cutting concern smeared across many files.

If a facet is undefined for the area, *naming it is the first deliverable*. Don't refactor toward an unstated target — a target that drifts each run is why refactoring efforts fail to terminate. Pin it as committed artifacts (CONTEXT.md, ADRs, dependency contracts).

ADRs are constraints, not suggestions: a move that contradicts an ADR is only surfaced when the friction is real enough to reopen the ADR, and is marked as such. Read the ADR log for **rejected and superseded** decisions and drop any move that re-proposes one — this is the shared memory that stops successive passes (and sibling code-health skills) from undoing each other. When you reject a move here for a load-bearing reason, write it back to the log so the next pass honors it.

## Phase 1 — Measure

Make progress objective. See [METRICS.md](METRICS.md) for the metric set and the ratchet.

1. **Detect the toolchain.** Find what the repo can already compute — cognitive complexity (`complexipy`, `clippy` cognitive-complexity, CRAP), duplication (`jscpd`, PMD CPD), cycles (`import-linter`, `dependency-cruiser`, `madge`, `cargo-modules`), dead code (`knip`, `vulture`, `ts-prune`), suppression counts (grep). Don't report a metric the repo can't reproduce — an unverifiable number is worse than none (and gets the tool switched off; see METRICS.md on false-positive discipline).
2. **Bootstrap the ratchet if absent.** No `baselines.json` → scaffold one (engineering-gates.md, §1), seeding every ceiling at the current actual. Now improvements have somewhere to be recorded.
3. **Rank hotspots by churn × complexity.** `git log --format= --name-only <since> | sort | uniq -c | sort -rn` gives churn; multiply by the complexity metric. Complexity in untouched code is nearly free — spend effort where change concentrates.
4. **Emit the starting scorecard** — the exact metrics Phase 6 will diff.

## Phase 2 — Diagnose

Fan out one `Explore` subagent per dimension; collect candidate **moves**. Dimensions:

- **God functions & data clumps** — `ai/audits/god-functions.md` here; DE-SLOP.md §"God functions" elsewhere.
- **Duplication** (knowledge / implementation / config) — `ai/audits/duplication.md`; DE-SLOP.md §"Duplication".
- **Coupling** (temporal, hidden side effects, dependency direction) — `ai/audits/coupling.md`; ONTOLOGY-AND-HIERARCHY.md §"Coupling".
- **Abstractions** (missing / premature / wrong-level / semantic-duplicate) — `ai/audits/abstractions.md`; DE-SLOP.md §"Abstractions".
- **AI slop** — DE-SLOP.md §"The AI-slop catalog".
- **Semantic duplication** — the token → embeddings → confirm pipeline in DE-SLOP.md, for Type-3/4 clones the audits miss.
- **Naming / hierarchy drift** — names not in the ontology; layout that screams the framework. ONTOLOGY-AND-HIERARCHY.md.

Each move records: **files**, **friction** (named in LANGUAGE.md + domain vocabulary), **proposed change** (plain English), **benefit** (locality/leverage + *which metric it moves*), and a rough **risk/effort**.

## Phase 3 — Rank

The order is the whole game — a bad order makes later moves redo earlier ones. Priority tiers:

1. **Cycles first.** A dependency cycle blocks clean layering and makes every other move in the cluster ambiguous. Break it (dependency inversion, or extract the shared element into its own module) before anything else in that cluster.
2. **Preparatory tidies with high downstream fan-out.** Kent Beck: "make the change easy (this may be hard), then make the easy change." A small structural tidy that unblocks five other moves outranks a flashy one that unblocks none. The Mikado leaf with the most dependents wins.
3. **Wrong abstractions.** Re-inline before re-abstracting (Metz: "the wrong abstraction is more expensive than duplication"). Extract/dedup is *suggested and reversible*, never automatic — honor the rule of three (1 caller: inline; 2: wait; 3+ and the shape is stable: abstract). An abstraction is only justified if it is *deep* and points *toward* stability; a shallow abstraction that adds a back-edge is worse than the duplication it replaced.
4. **De-slop hotspots.** Work the churn×complexity leaders; deepest modules first (highest leverage per edit).
5. **Rename / relocate to the ontology.** Last. Renaming while code is still moving creates churn and merge pain; do it once dependencies are settled.

Within a tier, weight by churn×complexity (impact) × leverage (locality gained) ÷ risk×effort.

## Phase 4 — Converge

Execute moves with the discipline that keeps each one safe and reviewable.

### The per-move loop

```
pick the top-ranked move
  → if non-trivial: Mikado experiment (try it naively)
       → if it fans out: revert to green, record prerequisites as leaves, recurse on a leaf
  → decompose into atomic, behavior-preserving steps
  → for each step:
       structure-only edit (one hat)
       run affected tests
       if red and not an expected transient: fix or revert
       commit (structure commit, separate from any behavior change)
  → re-measure the move's target metric; confirm it moved the right way
  → ratchet (Phase 5) before starting the next move
```

### The discipline, and why

- **Two hats (Kent Beck).** Every edit is *either* a structure change *or* a behavior change, never both. Structure changes are behavior-preserving and committed separately so review and `git bisect` stay clean. Mixing them is how "refactors" smuggle in bugs.
- **Atomic steps.** Refactoring research (RefactorBench, SWE-Refactor) is blunt: models — and people — land atomic, single-file refactors reliably and fail at compound, cross-file ones. Decompose until each step is independently testable. Never big-bang.
- **Tolerate transient red.** A correct refactor often passes through a temporarily-broken intermediate state (the #1 silent killer in RefactorBench was agents refusing to enter one). Checkpoint, allow red mid-step, drive back to green before the step is "done."
- **Verify by tests and structure, not diffs.** Behavior preservation is proven by the suite passing and the AST having the intended shape — never by the diff looking right.
- **Deterministic tools for the mechanical bulk.** Rename, extract, guard-clause flattening, dead-code removal: route through codemods (ast-grep, OpenRewrite, comby) where they exist. They are behavior-preserving by construction and free your judgment for the parts a codemod can't express — *which* abstraction, naming, semantic dedup.
- **Auto-fix vs grill.** Auto-apply the mechanical and unambiguous (dead code, unused imports, guard clauses, lookup-table-for-if-chain, dedup into an existing home). Grill the user on judgment: a new abstraction, an interface/seam change, anything on the public surface or touching an ADR. Default to grilling when uncertain — a wrong autonomous architectural move costs more than the question.

### Sweeping single moves

When one move is too large to ship atomically, keep `main` releasable throughout:

- **Branch by abstraction** — introduce an abstraction over the thing changing, migrate callers to it one at a time, build the new implementation behind it, then delete the old.
- **Parallel change / expand–contract** — *expand* the interface to support old and new, *migrate* callers incrementally, *contract* by removing the old. You must reach contract; a half-migrated state is a regression, not a rest stop.

Both forbid a permanently-dual state — the same "no competing versions" rule the ratchet enforces.

## Phase 5 — Ratchet

The step that turns cleanup into convergence. See engineering-gates.md §1 for the full mechanics.

- **Lower the baselines.** Tighten each `baselines.json` ceiling to the new actual. The monotonic guard means ceilings only fall; a future regression fails CI.
- **Encode satisfied constraints as CI contracts.** Zero cycles in a cluster → write the acyclic/layering rule into the dependency linter so it can't come back. This is Google LSC's "cleanup + prevention" step, and it is what makes the steady state *stay* steady instead of re-rotting one PR at a time.
- **No gaming.** Comment/blank stripping, `dict[str, Any]` → `dict[str, object]` type-laundering, landing a file at exact-fit — all forbidden. A clean longer file beats a mangled shorter one; LOC is a proxy, never the target.

## Phase 6 — Report & repeat

- **Scorecard diff** — LOC, duplication %, #functions-over-cognitive-complexity, dependency cycles, suppression counts, and the **refactored-vs-added ratio** (lines moved/consolidated vs lines added; the de-slop north star).
- **Decide:** loop if the area hasn't converged *and* the next move still pays for itself; otherwise stop.

### Termination — the area has converged when all hold

- The ranked move list is empty (every prerequisite leaf resolved).
- Dependency cycles = 0; nothing sits in the dependency "zone of pain" (stable + concrete) or "zone of uselessness" (abstract + unstable).
- Every dependency contract is green in CI and ratcheted.
- Every module name maps to an ontology term; the top-level structure screams the domain.
- No partially-migrated (expand-without-contract) states remain.
- **No move in the pass undid a decision recorded in the ADR log.** If a pass keeps reversing a prior pass's work, that's oscillation, not convergence — stop and record the contested decision instead of flip-flopping it.

### The economic brake

Even before full convergence, **stop when the next move costs more than its discounted future payoff.** Over-tidying is procrastination (Beck, *Tidy First?*; Dodds, AHA). Convergence is reached *or abandoned with reason* — a move rejected on economics is worth an ADR so the next pass doesn't re-propose it.
