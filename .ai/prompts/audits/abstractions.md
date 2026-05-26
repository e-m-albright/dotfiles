---
name: audit-abstractions
description: Audit prompt for abstraction quality — premature, missing, leaky, and wrong-level abstractions plus semantic duplication
---

# Design Audit: Abstraction Quality

You are auditing this codebase for abstraction problems: premature abstractions, missing abstractions, leaky abstractions, and duplicated logic that should be shared.

## What to look for

### Missing Abstractions
- Two or more functions that do the same thing slightly differently (DRY violation on knowledge, not just code)
- Repeated patterns across files in the same directory that could be a shared helper or base class
- `cast`, `Any`, `# type: ignore`, or `as any` at module boundaries — the abstraction is leaking

### Premature Abstractions
- Abstractions with only one concrete caller (Rule of Three violation)
- Configuration/flexibility that is never actually varied
- Base classes with only one subclass

### Wrong Level of Abstraction
- Functions that mix concerns from different layers (e.g., HTTP + business logic + database in one function)
- Pure Core / Imperative Shell violations: computation tangled with I/O

### Semantic Duplication (not textual)
- Two modules that solve the same problem with different approaches
- Parallel registries or lookup tables for the same concept
- Multiple ways to do the same thing with no clear canonical path

## What to do

For each finding:
1. Classify it: Missing / Premature / Wrong Level / Semantic Duplicate
2. Name the specific files and functions involved
3. Propose a concrete fix: what to extract, merge, inline, or restructure
4. Rate severity: how much confusion or drift will this cause if left unfixed?

## Scope

Default: the whole codebase. Prioritize cross-directory patterns where the same concept appears in multiple subsystems (frontend + backend, multiple services, multiple language layers).

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number.
- Distinguish *knowledge duplication* (bad — same business rule encoded twice) from *code duplication that encodes different decisions* (acceptable — coincidentally similar code paths that may diverge).
