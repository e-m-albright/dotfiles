# Ontology & Hierarchy

How to give a codebase an organizing ontology, a directory hierarchy that reflects it, and a dependency structure that forms a clean hierarchy instead of a tangle. Also the Phase-2 diagnostic brief for coupling, cycles, and naming drift.

The chain is: **ubiquitous language → bounded contexts → package-by-feature → idiomatic internals → acyclic, stably-directed dependencies.** Naming is the backbone; the directory tree should be a literal index of the domain.

## Ontology: the ubiquitous language

A domain model works as a *ubiquitous language* — one vocabulary shared by the code and the people who reason about it. The failure it prevents: the same word meaning subtly different things in different parts of the system (Fowler's utility-company "meter," fine in conversation, fatal in code).

For this skill, the glossary is not documentation — it is the **naming authority** for modules:

- A module's name must be a term in the ubiquitous language. A name that isn't is a diagnostic finding (rename, or add the term if it's a real, missing concept).
- Read `CONTEXT.md` / `CONTEXT-MAP.md`, or a `## Domain Language` section in `AGENTS.md`. Create it lazily when a refactor names a concept that belongs there (same discipline as `/grill-with-docs`).
- **Bounded contexts** scale the model: where the language changes, you have a different context, and *that boundary is where a top-level package boundary belongs.* A concept that means two things (Customer in sales vs. in billing) is *mapped* between contexts, not unified into one muddy model.

## Hierarchy: screaming, package-by-feature

The top-level structure should reveal **what the system does**, not **what it's built with.** When you look at the top directory, it should scream "Billing, Ingest, Scheduling," not "Controllers, Services, Repositories" or "Rails, Django, Spring." Frameworks are tools used *inside* the structure, not the structure itself. The test: you should be able to exercise the use cases with the framework absent.

- **Package-by-feature, not by-layer.** Layer packages (`controllers/`, `services/`, `repositories/`) have low cohesion — unrelated things share a folder because they share a *kind* — and force everything public to be wired across layers. Feature packages put everything for one capability together: high cohesion, low coupling, and they permit package-private visibility (real encapsulation you can't get across layer packages).
- **Layer only *inside* a feature**, and only idiomatically for the language.
- The diagnostic: a layout that screams the framework, or a feature whose pieces are scattered across layer folders, is a hierarchy move.

## Module depth (the idiomatic core)

Idiomatic design, across languages, reduces to **deep modules**: a large, capable implementation behind a small interface (Ousterhout). Complexity = dependencies + obscurity; a deep module minimizes both for its callers.

- **Information hiding** is the lever — clients see an abstract view; the implementation is free to be complex and to change.
- **Define errors out of existence.** Redesign the semantics so the error case can't arise rather than making every caller handle it (Ousterhout's `unset` example: "the variable ends up not set" instead of "throws if already unset").
- Per language, this expresses differently — Go: small consumer-defined interfaces + `error` returns; Rust: `Option`/`Result` and making illegal states unrepresentable; Python: a small public surface, `__all__`/underscore for hiding. The invariant is constant: *small interface, large hidden implementation, errors designed away.* Per-language taste lives in `docs/stacks/`.

See [LANGUAGE.md](LANGUAGE.md) and [DEEPENING.md](DEEPENING.md) for the deepening vocabulary and the safe mechanics.

## Dependency structure as hierarchy

A clean architecture's dependency graph is a **hierarchy, not a web.** Two principles and a target:

- **Acyclic Dependencies Principle** — the dependency graph of modules/packages has *no cycles.* Break a cycle by (a) dependency inversion (introduce an interface so an arrow flips) or (b) extracting the shared element both sides need into its own module. A cycle is always breakable.
- **Stable-Dependencies / Stable-Abstractions** — depend in the direction of stability, and the more stable a module, the more abstract it should be. Instability `I = Ce / (Ca + Ce)` (efferent ÷ total coupling). A module that is *stable + concrete* sits in the **zone of pain** (everything depends on it, nothing can change it) — a high-priority finding. *Abstract + unstable* is the **zone of uselessness**.
- **Target shape** — order modules so the dependency matrix is **lower-triangular**: a perfectly layered structure with no cycles. A cell above the diagonal is an up-the-hierarchy dependency (a layering violation or a cycle). Driving the matrix toward triangular is a single, visualizable convergence target.

### Coupling (Phase 2 brief)

Findings to surface, with severity:
- **Temporal coupling** — operations that must run in a hidden order; preconditions checked after expensive work (fail-fast violation). *Fix:* encode the order in the types, check preconditions first.
- **Hidden side effects** — a signature that doesn't reveal its I/O or mutation; a query that writes (command-query violation). *Fix:* make effects visible in the type; separate command from query.
- **Shared mutable state / unbounded fan-out** — async without synchronization; `gather`/`join_all` without a bound. *Fix:* bound concurrency; isolate state.
- **Wrong dependency direction** — a stable module (core/domain) importing a volatile one (routes/CLI/UI). *Fix:* invert.
- **Law of Demeter** — `a.b.c.d()` reaching through layers. *Fix:* tell-don't-ask, or add the method to the right module.

## Enforcement: make the hierarchy a ratcheted contract

Once an area is acyclic and correctly layered, **encode it so it can't regress** — this is the Phase-5 ratchet for structure:

| Language | Tool | Enforces |
|---|---|---|
| Python | **import-linter** | `layers`, `forbidden`, `independence`, acyclic contracts in `.importlinter`; `lint-imports` fails CI. |
| JS/TS | **dependency-cruiser** | custom rules: circular deps, orphans, layering violations; graph output. |
| JS/TS | **madge** | visual graph + cycle detection. |
| Java | **ArchUnit** | architecture rules as plain tests: layers, slices, cycle checks. |
| Rust | **cargo-modules** | module-tree + dependency graph for review. |
| .NET / multi | **NDepend / Lattix** | dependency-structure-matrix analysis, layering, cycles. |

A passing layer/acyclic rule written into one of these is a *fitness function*: the structure is now defended by CI, and a future change that re-tangles it fails the build. That is how the architecture stays clean instead of re-rotting one PR at a time.

## Balancing dedup against the hierarchy

Deduplication and a clean dependency hierarchy pull against each other: every abstraction you extract adds a dependency edge and can reduce stability or create a cycle. So an "extract to remove duplication" move is only justified when the result is **deep** (real leverage) *and* points **toward** stability. A shallow shared helper that introduces a back-edge is strictly worse than the duplication it replaced. When in doubt, prefer the duplication and wait for the rule of three — and treat every extract as reversible (re-inlining is a legitimate move, not a failure).
