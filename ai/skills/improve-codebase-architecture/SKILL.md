---
name: improve-codebase-architecture
description: A repeatable convergence engine that drives a codebase toward simpler, deduplicated, idiomatic, ontologically-organized code and ratchets the gains in so they can't regress. Measures (static grading), diagnoses (god functions, duplication, coupling, weak abstractions, AI slop), ranks by churn×complexity, applies behavior-preserving refactors (auto-fix mechanical, grill judgment calls), then lowers the baselines. Use when the user wants to "improve architecture", "find refactor opportunities", "simplify this codebase", "deduplicate", "reduce LOC", "de-slop / un-AI-slop the code", "make this more idiomatic", "tighten the module boundaries", "ratchet down complexity", "converge the codebase", "deepen modules", "this feels coupled", or "where are the seams?". For a single pre-merge diff review use /review; for a one-shot quality cleanup of the current diff use /simplify; this skill is the whole-codebase, multi-pass convergence loop.
metadata:
  source_url: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md
  source_commit: 733d312884b3878a9a9cff693c5886943753a741
  ported_at: 2026-05-07
  adaptations: Expanded from a conversational module-deepening tool into a full measure→diagnose→rank→converge→ratchet→report convergence engine. Deepening is now one move-type in Phase 4. Added references/CONVERGENCE-LOOP.md, references/METRICS.md, references/DE-SLOP.md, references/ONTOLOGY-AND-HIERARCHY.md (synthesized from CodeScene Code Red, GitClear AI-slop data, RefactorBench/SWE-Refactor, SonarSource cognitive complexity, the Mikado Method, Google LSC, Ousterhout, Metz/Dodds). Reuses the repo's ai/audits/*, review health rubric, and engineering-gates ratchet rather than duplicating them.
---

# Improve Codebase Architecture

A **convergence engine**: a repeatable loop that pushes a codebase toward a named steady state — simpler, deduplicated, idiomatic, organized by a real ontology — and **ratchets each gain in** so the next change can't undo it. The aim is code a grumpy 15-year principal engineer would approve without comments: deep modules, no slop, measurably better every pass.

This is the whole-codebase, multi-pass sibling of the diff-scoped tools. Use `/review` to grade a single PR and `/simplify` to clean one diff; use **this** when you want to drive an area (or the whole repo) toward convergence over several passes and lock the result in.

## What it does

Six phases, run as a loop until the area converges:

```
0. Target    — define the steady state (ontology, hierarchy, depth, dependency shape)
1. Measure   — establish/refresh the scorecard; rank hotspots by churn × complexity
2. Diagnose  — fan out parallel audits → candidate "moves"
3. Rank      — order moves: cycles → preparatory tidies → wrong abstractions → de-slop → rename
4. Converge  — execute each move in atomic, behavior-preserving, test-verified steps
5. Ratchet   — lower the baselines, encode satisfied constraints as CI contracts
6. Report    — before/after scorecard; check termination; loop or stop
```

It pushes on five fronts at once, each with a measurable proxy:

| Goal | What it means | Proxy it moves |
|---|---|---|
| **Simplify** | deep modules, errors defined out of existence, less nesting | cognitive complexity, # functions over threshold |
| **Deduplicate** | one home per concept; reuse over re-implement | duplication %, "refactored-vs-added" ratio |
| **Organize** | a hierarchy that screams the domain; names from the ubiquitous language | naming/ontology coverage, package cohesion |
| **De-slop** | strip AI bloat: defensive checks, speculative abstraction, copy-paste | suppression counts, slop-smell count, LOC (honest) |
| **Idiomatic** | per-language taste; acyclic, stably-directed dependencies | dependency cycles = 0, layering contract green |

It does **not** hunt for bugs (that's `/review`) and does **not** invent flexibility for needs that don't exist (YAGNI — see Phase 3). It is **hybrid-autonomous**: it auto-applies mechanical, behavior-preserving fixes and *grills you* on judgment calls.

## Vocabulary

Use these terms exactly in every suggestion — consistent language is the point. Don't drift into "component," "service," "API," or "boundary." Full definitions in [references/LANGUAGE.md](references/LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know: types, invariants, error modes, ordering, config. Not just the type signature.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage; **shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Move** — one ranked refactoring (deepen, dedup, de-slop, break-cycle, rename-to-ontology…). The unit this skill plans, executes, and ratchets.
- **Convergence** — the area reaches the Phase-0 target and every gain is ratcheted; the move list is empty and CI contracts hold.

Key principles (full list in [references/LANGUAGE.md](references/LANGUAGE.md)):

- **Deletion test** — imagine deleting the module. If complexity vanishes, it was a pass-through; if it reappears across N callers, it earned its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = a real one.**

This skill is _informed_ by the project's domain model: the domain language names good seams; ADRs record decisions it must not re-litigate.

## The loop

Read [references/CONVERGENCE-LOOP.md](references/CONVERGENCE-LOOP.md) for the full phase mechanics, the Mikado/expand-contract execution discipline, and the termination conditions. The summary:

### Phase 0 — Target (define "done")

Without a named steady state, refactoring churns forever. Establish the target from what already exists, creating docs lazily as decisions crystallize:

- **Ontology** — read the domain glossary (`CONTEXT.md`/`CONTEXT-MAP.md`, or a `## Domain Language` section in `AGENTS.md`) and any ADRs in the area. This is the *naming authority* for modules. See [references/ONTOLOGY-AND-HIERARCHY.md](references/ONTOLOGY-AND-HIERARCHY.md).
- **Hierarchy** — the directory tree should be a literal index of the domain (package-by-feature, top-level dirs that "scream" the domain, not the framework).
- **Dependency shape** — the target is zero cycles and dependencies pointing toward stability (the dependency matrix trends lower-triangular).
- **Depth** — deep modules; errors defined out of existence.

If the area lacks any of these, say so — naming the target is itself the first valuable output.

### Phase 1 — Measure

Establish the scorecard so progress is objective, not vibes. Read [references/METRICS.md](references/METRICS.md) for the metric set and ratchet mechanics.

- Detect and run the repo's static tools (cognitive-complexity, duplication, dependency cycles, dead code, suppression counts). Don't invent metrics the repo can't compute.
- **Bootstrap the ratchet if absent.** If there's no `baselines.json`, scaffold one per [docs/knowledge/engineering-gates.md](../../../docs/knowledge/engineering-gates.md) (in this repo) or the project's equivalent, seeding ceilings at *current actuals* — then the loop tightens them. This is what makes "ratchet down measurably" real even in a repo with no gates.
- **Rank hotspots by churn × complexity.** Complexity in code nobody touches is nearly free; spend effort where change concentrates (CodeScene's central finding — see METRICS.md). Use `git log` to get churn.
- Emit the starting scorecard (the same metrics Phase 6 will diff).

### Phase 2 — Diagnose

Fan out parallel `Explore` subagents, one per dimension, each returning candidate moves. **In this repo**, point them at the canonical audit prompts in [ai/audits/](../../audits/) (`god-functions`, `duplication`, `coupling`, `abstractions`). **In any other project**, use the self-contained dimension briefs in [references/DE-SLOP.md](references/DE-SLOP.md) (god functions, data clumps, duplication, weak abstractions, conditional bloat, the AI-slop catalog) and [references/ONTOLOGY-AND-HIERARCHY.md](references/ONTOLOGY-AND-HIERARCHY.md) (coupling, cycles, naming/hierarchy drift). Add a semantic-duplication pass (token → embeddings → confirm) per DE-SLOP.md.

Each candidate move records: files, the friction (in LANGUAGE.md + domain vocabulary), the proposed change in plain English, and the benefit in **locality/leverage** and **which metric it moves**.

### Phase 3 — Rank

Order the moves so the effort converges instead of thrashing. Priority (full rationale in CONVERGENCE-LOOP.md):

1. **Cycles first** — they block clean layering; break via dependency inversion or extract-shared-package.
2. **Preparatory tidies with high downstream fan-out** — "make the change easy, then make the easy change." Unblock the most other moves.
3. **Wrong abstractions** — re-inline before re-abstracting (Metz: "duplication is cheaper than the wrong abstraction"). Treat extract/dedup as *suggested and reversible*, never automatic; honor the rule of three.
4. **De-slop hotspots** — the churn×complexity leaders, deepest modules first.
5. **Rename / relocate to the ontology** — last, once dependencies are clean, so renames don't fight moving code.

Weight within each tier by churn×complexity (impact), leverage (locality gained), and inverse risk/effort.

### Phase 4 — Converge

Execute each move with refactoring discipline (full mechanics + the per-move loop in CONVERGENCE-LOOP.md):

- **Two hats** — change *structure* or *behavior*, never both in one step; structure moves are behavior-preserving and get their own commit.
- **Atomic steps** — decompose every move into the smallest individually-testable edits. LLMs (and humans) fail at big-bang compound refactors; atomic + verify-after-each is what makes it land.
- **Verify after each step** — run the affected tests; tolerate a temporarily-red intermediate state, but always drive back to green before moving on. Verify behavior by tests and structure, never by diff-matching.
- **Mikado for anything non-trivial** — try the move naively; if it fans out, revert to green and record the prerequisites as graph leaves, then work leaves-first.
- **Deterministic tools for the mechanical bulk** — route rote, behavior-preserving transforms (rename, extract, guard-clause flattening, dead-code removal) through codemods (ast-grep, OpenRewrite, comby) where available; reserve your own judgment for *which* abstraction, naming, and semantic dedup.
- **Auto-fix vs grill** — auto-apply the unambiguous, mechanical, behavior-preserving fixes (dead code, unused imports, guard clauses, lookup tables replacing if/elif chains, dedup-to-an-existing-home). Grill the user on judgment calls (a new abstraction, an interface/seam change, anything touching the public surface or an ADR). Default to grilling when uncertain. The grilling loop is the original module-deepening conversation — see below.

**The grilling loop (judgment moves).** Walk the design tree with the user — constraints, dependencies, the shape of the deepened module, what sits behind the seam, which tests survive. Side effects happen inline:
- Naming a module after a concept not in `CONTEXT.md`? Add the term (same discipline as `/grill-with-docs` — see [../grill-with-docs/references/CONTEXT-FORMAT.md](../grill-with-docs/references/CONTEXT-FORMAT.md)). Create the file lazily.
- User rejects a move with a load-bearing reason a future explorer would need? Offer an ADR so the next pass doesn't re-suggest it (see [../grill-with-docs/references/ADR-FORMAT.md](../grill-with-docs/references/ADR-FORMAT.md)). Skip ephemeral or self-evident reasons.
- Exploring alternative interfaces for a deepened module? See [references/INTERFACE-DESIGN.md](references/INTERFACE-DESIGN.md). Deepening mechanics and dependency categories: [references/DEEPENING.md](references/DEEPENING.md).

### Phase 5 — Ratchet

Lock the gains in so the codebase can't re-rot — this is the difference between a one-shot cleanup and *convergence*:

- **Lower the baselines.** Tighten every `baselines.json` ceiling to the new, better actual. Never raise silently (the monotonic guard in engineering-gates.md). LOC, duplication, and suppression counts only move down.
- **Encode satisfied constraints as CI contracts.** Once an area has zero cycles or respects a layering rule, write it into the dependency linter (import-linter / dependency-cruiser / ArchUnit / cargo-modules) so a future change *can't* reintroduce it. This is the "cleanup + prevention" step that stops infinite churn.
- **No gaming.** Never strip comments/blanks or launder types to slip under a ceiling; a clean longer file beats a mangled shorter one. When a metric is at floor, do the real refactor or change the *formula* — see the anti-gaming rules in engineering-gates.md.

### Phase 6 — Report & repeat

Show the before/after scorecard: LOC, duplication %, #functions-over-cognitive-complexity, dependency cycles, suppression counts, and the **refactored-vs-added ratio** (the de-slop north star — GitClear data shows AI assistants *add* code instead of consolidating; this loop inverts that). Then check the termination conditions (CONVERGENCE-LOOP.md). If the area hasn't converged and the next move still pays for itself, loop. Stop when the move list is empty, the contracts hold, **or** the economics turn (over-tidying is procrastination — the AHA/Tidy-First brake).

## Scope of a run

**Default: a bounded hotspot set.** Pick the top-N churn×complexity hotspots (or a path the user names) and converge *those* to target, then report. Bounded, reviewable, and repeatable — run again for the next set, the way large orgs shard big changes. Don't try to fix the whole repo in one invocation by default.

**Escalation: whole-codebase sweep.** When the user explicitly asks for a full sweep (or the repo is small), widen scope to the entire codebase. For a large repo this is the natural place to escalate to a multi-agent `Workflow` (fan out diagnose across the tree → dedup → verify → ratchet) — but only when the user opts into that, since Workflow is Claude-Code-only. The inline subagent path is the portable default.

## References

- [references/CONVERGENCE-LOOP.md](references/CONVERGENCE-LOOP.md) — the six phases in depth, execution discipline (Mikado, expand-contract, branch-by-abstraction), and termination conditions.
- [references/METRICS.md](references/METRICS.md) — the minimal hard-to-game metric set, churn×complexity ranking, ratchet/baseline mechanics, and false-positive discipline.
- [references/DE-SLOP.md](references/DE-SLOP.md) — the AI-slop smell catalog, the conditional-bloat reduction transforms with a selection heuristic, and the semantic-dedup pipeline.
- [references/ONTOLOGY-AND-HIERARCHY.md](references/ONTOLOGY-AND-HIERARCHY.md) — ubiquitous-language → bounded-context → package-by-feature → screaming architecture, plus dependency hierarchy (acyclic, stably-directed) and per-language enforcement tools.
- [references/LANGUAGE.md](references/LANGUAGE.md) — the architecture vocabulary used in every suggestion.
- [references/DEEPENING.md](references/DEEPENING.md) — how to deepen a cluster of shallow modules safely given its dependencies.
- [references/INTERFACE-DESIGN.md](references/INTERFACE-DESIGN.md) — exploring alternative interfaces for a deepened module.

Companion docs in this repo (canonical sources this skill reuses rather than duplicates): [docs/engineering-philosophy.md](../../../docs/engineering-philosophy.md) (12 principles), [docs/knowledge/engineering-gates.md](../../../docs/knowledge/engineering-gates.md) (ratchet mechanics), [ai/audits/](../../audits/) (diagnostic prompts), and the [review](../review/SKILL.md) health rubric.

## Sources
- Adapted from [mattpocock/skills/engineering/improve-codebase-architecture](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/improve-codebase-architecture/SKILL.md) (ported 2026-05-07, MIT). Expanded into a convergence engine; original deepening flow retained as one Phase-4 move-type.
- New references synthesize: CodeScene *Code Red* (Tornhill & Borg, TechDebt 2022); GitClear *AI Copilot Code Quality 2025*; *RefactorBench* (ICLR 2025) and *SWE-Refactor* (2026); SonarSource *Cognitive Complexity*; the *Mikado Method*; *Software Engineering at Google* ch. 22 (LSC); Ousterhout *A Philosophy of Software Design*; Metz *The Wrong Abstraction* and Dodds *AHA Programming*; Fowler *Refactoring* 2e; Ford et al. *Building Evolutionary Architectures*.
