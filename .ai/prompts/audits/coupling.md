# Design Audit: Coupling and State Management

You are auditing this codebase for coupling problems: temporal coupling, hidden side effects, shared mutable state across async boundaries, and Law of Demeter violations.

## What to look for

### Temporal Coupling
- Operations that must happen in a specific order, but nothing in the code enforces that order
- Preconditions checked after expensive computation instead of before (Fail Fast violation)
- Initialization sequences where reordering steps silently produces wrong results

### Hidden Side Effects
- Functions whose type signatures do not reveal that they write files, make network calls, or mutate external state
- Functions named as queries that also perform mutations
- Command-Query Separation violations: a function that returns a value AND changes state

### Shared Mutable State
- Mutable state accessed from multiple async tasks without explicit synchronization
- `asyncio.gather()` or `tokio::join!` where tasks share a mutable reference
- Global or module-level mutable state mutated during request handling

### Law of Demeter / Train Wrecks
- Chains like `obj.field.subfield.method()` — reaching through layers
- Handlers that traverse multiple levels of nested data to extract values

### Dependency Direction
- Volatile modules (routes, CLI, UI) being imported by stable modules (core, domain)
- Core logic importing from framework-specific code

## What to do

For each finding:
1. Name the coupling type and severity (will-break vs. friction vs. code-smell)
2. Name the specific files, functions, and the relationship between them
3. Propose how to decouple: extract, inject, use channels, enforce order via types
4. Note if this is in a hot path (request handling, critical user flow, pipeline)

## Scope

Default: the whole codebase. Prioritize async-heavy modules (queue workers, request handlers, streaming pipelines) where coupling bugs become production incidents.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number.
- Flag async-safety issues with HIGH priority — these are production incident candidates.
