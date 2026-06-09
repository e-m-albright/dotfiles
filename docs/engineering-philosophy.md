# Engineering Philosophy

> Universal principles for any codebase. Distilled from a private code-health manifesto. Cross-referenced by the agent rule kernel (`ai/agents/shared/rules.md`), `ai/audits/`, and `ai/skills/review/`.

Agentic programming amplifies whatever foundation you build on. Strong foundation compounds velocity: agents reuse clean abstractions, follow typed contracts, produce code that slots into the existing architecture without friction. Weak foundation compounds debt: agents copy-paste patterns, invent parallel registries, produce code that works today and rots tomorrow.

Code health is not a cleanup task you schedule between features. It is the single highest-leverage investment for maintaining velocity in an agentic codebase.

When you notice a foundational crack while doing other work, surface it and address it — or formally defer it with a written reason. The tiebreaker on any judgment call is *which is more correct in the long run*, not which is faster to ship; prefer fewer, deeper, more correct changes over many shallow patches. This is **not** a license to gold-plate: scope the depth to the subdomain that earns it (see the prune↔align tiebreak in the [code-health portfolio](knowledge/code-health-portfolio.md)), and propose any rewrite explicitly before taking it on — don't surprise the reader with scope.

Every principle here should map to at least one automated gate in any project that adopts it. If you cannot enforce it, do not claim it.

---

## The Principles

### 1. The compiler is the first reviewer

Every invariant that can be checked statically, is. A type error caught in the editor is infinitely cheaper than one caught in production. When the compiler can't help, the linter should. When the linter can't help, CI should.

**Gate examples**: `clippy -D warnings`, `ruff`, `pyright strict`, `biome`, `tsc --noEmit`, `svelte-check`.

### 2. Type the domain, not the plumbing

`string` is not a type. `dict[str, Any]` is not a contract. Every domain concept — status values, channel types, pipeline stages — gets an enum, union, or model, never a magic string compared at call sites. And a bare literal is not a name: a number or string that carries meaning (a timeout, a limit, a status key) gets a single named constant or enum member, not a copy at each use. Types and named constants are documentation the compiler enforces.

**Gate examples**: `dict[str, Any]` count ratchet; enum discipline checks; `as any` count ratchet; magic-value/magic-number lints (advisory) and the "Magic Values" structural smell in the review rubric.

### 3. One source of truth per concept

Every domain value lives in one typed export. Everything else imports. If adding a route, status, or channel requires editing more than one file, the architecture is wrong.

**Gate examples**: contract-drift tests; `knip` dead-export detection.

### 4. Boundaries are contracts

Validate at edges, trust types inside. Pydantic at every Python boundary, schemars/serde for Rust API shapes, strict TypeScript at the web layer. Inside the boundary: trust your types. Outside: trust nothing.

**Gate examples**: `pyright strict`, schema-freshness tests, runtime validators on every external entry point.

### 5. Simplicity is the goal — small files are a proxy

We do not limit lines of code; we pursue reusability and clarity. LOC is a proxy for how well complexity is being managed. When a file grows, the question is "are we duplicating or mixing concerns?" not "is it too long?". When scope demands complexity, earn it through composition.

**Gate examples**: file-size ratchet (per-file ceiling, monotonic decrease); cyclomatic-complexity suppressions can only decrease.

### 6. Dead code is dead weight

Delete confidently; git has history. Commented-out code is a lie that decays faster than any other artifact. `#[allow(dead_code)]` and equivalent suppressions are deferred decisions with a shelf life.

**Gate examples**: `vulture`, `cargo machete`, `knip`, fallow-export checks.

### 7. Every exception is an event

No `except Exception` without structured context. No `.catch(() => {})` without an intentional reason. Silent recovery is a bug unless it's logged, bounded, and intentional.

**Gate examples**: `except Exception` count ratchet; policy checks for silent catches.

### 8. Concurrency is bounded

Every `gather()` has a semaphore. Every `join_all` has a `buffer_unordered(N)`. Unbounded fan-out is a production incident waiting for load.

**Gate examples**: advisory review on async-heavy diffs; lints for unbounded concurrency primitives.

### 9. Observability is a design constraint, not an afterthought

Significant operations have spans/traces. Logs are structured with context (entity IDs, operation names). No bare string warnings. If a request can fail invisibly, the design is incomplete.

**Gate examples**: span coverage on critical paths; structured-log linter; observability audit.

### 10. Suppressions ratchet downward

When a check fires and you genuinely need to suppress it (`# noqa`, `# type: ignore`, `#[allow(...)]`, `// @ts-expect-error`), the count of suppressions can only decrease. Suppressions accumulate silently otherwise; the ratchet keeps the cost of each one visible.

**Gate examples**: per-suppression-kind count ratchet in `baselines.json`.

### 11. Tests verify behavior, not implementation

Tests mock at module boundaries, not internals. Fixtures are shared via factories, not copy-paste. A passing test should be evidence that the behavior is correct from the user's perspective — not that the current implementation didn't change.

**Gate examples**: skipped-test count ratchet; coverage floors per module; mocking-the-database lint.

### 12. Convention over configuration over code

Isolate what varies behind the cheapest stable seam. When a pattern repeats: first encode it as a convention (file naming, directory layout). If that's not enough, encode it as configuration (a registry, a typed enum, a single config file the rest imports). Only fall back to bespoke code when neither convention nor config can express it. The thing that changes lives in one declarative place; the code that consumes it stays closed to that change.

**Gate examples**: registry-derivation tests (one source, many derivations); naming-convention lints.

---

## Structural smells (what linters can't catch)

A per-change checklist for the things gates miss. If any fires, the design is asking to be reconsidered:

- **God function** — can you describe what it does without saying "and"? If not, split it.
- **Data clump** — 3+ primitives that always travel together are a missing struct/model.
- **Lying signature** — hidden I/O, mutation, or failure not in the type. Make effects visible.
- **Leaky boundary** — `cast`/`Any`/`as any`/`unwrap` at a module edge. The boundary isn't typed; fix the contract.
- **Impossible state** — can the type be constructed in a forbidden state? Make illegal states unrepresentable (enums over boolean soup, parse-don't-validate).
- **Temporal coupling** — methods that must be called in a hidden order. Encode the order in the types.
- **Humble object** — logic only testable end-to-end. Extract a pure core; leave a thin adapter.
- **Rule of three** — 1 caller → inline; 2 → wait; 3+ → abstract. Don't abstract on speculation.

### AI-generated code tends toward

These are the failure modes to watch when reviewing agent (or your own) output:

- **Primitive obsession** — strings/dicts where a domain type belongs.
- **Duplicating instead of reusing** — re-implementing an abstraction that already exists (agents don't always find it).
- **Speculative flexibility (YAGNI)** — config knobs, hooks, and generality for needs that don't exist yet.
- **External field names as domain vocabulary** — leaking an API's naming into the core instead of the project's ubiquitous language.
- **End-to-end-only testability** — logic that can't be unit-tested because it wasn't separated from its effects.

## How agents should use this

When you (the agent) are about to write or change code, ask which principles apply. When auditing, grade against these as the universal rubric (see `ai/skills/review/SKILL.md` for the full grading process).

These principles are universal; per-language taste (idioms, pick/avoid, gates) lives as reference in `docs/stacks/`. The principle is universal; the enforcement is local.

## Calibration

- **A overall** — "a grumpy 15-year principal engineer would approve without comments"
- **B overall** — "solid, some cleanup opportunities, nothing urgent"
- **C overall** — "functional but accumulating debt, needs a cleanup pass"
- **D overall** — "significant quality issues affecting maintainability"
- **F overall** — "actively harmful patterns that will cause production incidents"

Post-cleanup target: A-/B+. Below B should not merge without addressing the top action items.
