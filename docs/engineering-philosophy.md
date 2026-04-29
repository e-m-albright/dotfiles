# Engineering Philosophy

> Universal principles for any codebase. Distilled from the Ophira code-health manifesto. Cross-referenced by `.ai/rules/`, `.ai/prompts/audits/`, and `.ai/skills/code-quality-audit/`.

Agentic programming amplifies whatever foundation you build on. Strong foundation compounds velocity: agents reuse clean abstractions, follow typed contracts, produce code that slots into the existing architecture without friction. Weak foundation compounds debt: agents copy-paste patterns, invent parallel registries, produce code that works today and rots tomorrow.

Code health is not a cleanup task you schedule between features. It is the single highest-leverage investment for maintaining velocity in an agentic codebase.

Every principle here should map to at least one automated gate in any project that adopts it. If you cannot enforce it, do not claim it.

---

## The Principles

### 1. The compiler is the first reviewer

Every invariant that can be checked statically, is. A type error caught in the editor is infinitely cheaper than one caught in production. When the compiler can't help, the linter should. When the linter can't help, CI should.

**Gate examples**: `clippy -D warnings`, `ruff`, `pyright strict`, `biome`, `tsc --noEmit`, `svelte-check`.

### 2. Type the domain, not the plumbing

`string` is not a type. `dict[str, Any]` is not a contract. Every domain concept — status values, channel types, pipeline stages — gets an enum, union, or model. Types are documentation the compiler enforces.

**Gate examples**: `dict[str, Any]` count ratchet; enum discipline checks; `as any` count ratchet.

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

When a pattern repeats: first encode it as a convention (file naming, directory layout). If that's not enough, encode it as configuration (a registry, a typed enum). Only fall back to bespoke code when neither convention nor config can express it.

**Gate examples**: registry-derivation tests (one source, many derivations); naming-convention lints.

---

## How agents should use this

When you (the agent) are about to write or change code, ask which principles apply. When auditing, grade against these as the universal rubric (see `.ai/skills/code-quality-audit/SKILL.md` for the full grading process).

When projects adopt these principles, the per-language `.ai/rules/` files (Python, Rust, TypeScript, etc.) translate them into language-specific gates and patterns. The principle is universal; the enforcement is local.

## Calibration

- **A overall** — "a grumpy 15-year principal engineer would approve without comments"
- **B overall** — "solid, some cleanup opportunities, nothing urgent"
- **C overall** — "functional but accumulating debt, needs a cleanup pass"
- **D overall** — "significant quality issues affecting maintainability"
- **F overall** — "actively harmful patterns that will cause production incidents"

Post-cleanup target: A-/B+. Below B should not merge without addressing the top action items.
