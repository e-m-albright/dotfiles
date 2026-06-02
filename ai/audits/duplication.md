---
name: audit-duplication
description: Audit prompt for duplication — knowledge, implementation, and configuration. Distinguishes drift-prone duplication from coincidentally similar code.
---

# Design Audit: Duplication

You are auditing this codebase for duplication: repeated knowledge that has drifted, parallel implementations of the same concept, and copy-paste patterns that should be unified.

## What to look for

### Knowledge Duplication (high severity)
- The same business rule encoded in two places (e.g., status transitions defined in both backend and frontend)
- Parallel enums/constants for the same domain concept across services or layers
- The same validation logic implemented separately at multiple boundaries
- Identical SQL queries written by hand in 3+ places

### Implementation Duplication
- Functions that share >80% of their body and could be unified with a parameter
- Multiple modules with the same imports and skeleton, doing slightly different work
- Boilerplate that could be a decorator, macro, or higher-order function

### Configuration Duplication
- Constants redeclared in tests instead of imported from the source
- Environment variables read in multiple modules with their own defaults
- API endpoint URLs hardcoded in multiple call sites

### Acceptable Duplication (do NOT flag these)
- Two functions with similar shapes that encode *different decisions* — they may diverge as requirements evolve. Forcing unification creates the wrong abstraction (Rule of Three is about three real cases, not three look-alike cases).
- Test fixtures that are intentionally distinct (one verifies the happy path, another verifies the boundary case)

## What to do

For each finding:
1. Classify: Knowledge / Implementation / Configuration
2. Name the files and the duplicated content
3. Propose the canonical home and how the others should reference it
4. Rate severity: will-drift (knowledge), churn-tax (implementation), or aesthetic (configuration)

## Scope

Default: the whole codebase. Prioritize cross-layer duplication (frontend ↔ backend, app ↔ infrastructure) — that's where drift causes incidents.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially "One source of truth per concept".
- Distinguish knowledge duplication from acceptable code duplication. Be willing to leave look-alike code alone if it encodes different decisions.
