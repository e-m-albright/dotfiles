---
name: audit-structural
description: Structural-smell sweep — god functions, data clumps, arrow code, lying signatures, leaky boundaries, temporal coupling, parse-don't-validate, humble objects
---

# Design Audit: Structural Smells

You are auditing this codebase for the structural smells that linters can't catch — the design-level issues from `docs/engineering-philosophy.md`. Serves **P5 (Simplicity is the goal)** and **P4 (Boundaries are contracts)**.

## What to look for

### God Functions
- Functions you can't describe without saying "and" — split them
- Functions mixing I/O (file, network, DB) with computation
- More than 3 levels of nesting in business logic

### Data Clumps
- 3+ primitives that always travel together (passed, returned, initialized as a group) — a missing struct/model

### Arrow Code
- Deep `if`/`for` nesting that marches rightward; early-return guard clauses would flatten it
- Conditionals that could be a lookup table, polymorphism, or a decomposed predicate

### Lying Signatures
- Hidden I/O, mutation, or failure not visible in the type/signature
- Query-named functions that also mutate (Command-Query Separation violation)

### Leaky Boundaries
- `cast` / `Any` / `as any` / `unwrap` / `# type: ignore` at a module edge — the contract isn't typed
- Internal types leaking across a public API surface

### Temporal Coupling
- Methods that must be called in a hidden order; encode the order in the types instead

### Parse, Don't Validate
- Re-checking the same invariant at multiple call sites instead of parsing once into a type that makes the illegal state unrepresentable
- Boolean soup where an enum/union belongs

### Humble Objects
- Logic only testable end-to-end because it isn't separated from its effects — extract a pure core, leave a thin adapter

## How to report

For each finding: `file:line` and the function/type, name the smell, **severity** (structural-debt / friction / nit), and the concrete refactor — name the extracted function, the new struct, the guard clause, or the type that removes the recheck. NEVER auto-apply a refactor.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
