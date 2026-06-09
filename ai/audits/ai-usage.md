---
name: audit-ai-usage
description: AI-generated-code smell audit — primitive obsession, duplicated-not-reused logic, speculative flexibility (YAGNI), leaked external field names, end-to-end-only testability, over-defensive checks
---

# Design Audit: AI-Generated Code Smells

You are auditing this codebase for the failure modes that agent-written (and hand-written) code tends toward, per `docs/engineering-philosophy.md`'s "AI-generated code tends toward" list. Serves **P2 (Type the domain, not the plumbing)**, **P5 (Simplicity is the goal)**, and **P6 (Dead code is dead weight)**.

## What to look for

### Primitive Obsession
- `str` / `dict[str, Any]` / bare tuples where a domain type (enum, model, newtype) belongs
- Magic strings/numbers compared at call sites instead of one named constant or enum member

### Duplicating Instead of Reusing
- A helper, validator, or client re-implemented because the agent didn't find the existing one
- Two near-identical functions that should be one (watch the Rule of Three: 3+ callers → abstract)

### Speculative Flexibility (YAGNI)
- Config knobs, hooks, strategy interfaces, or generality for needs that don't exist yet
- Single-implementation abstractions, unused parameters, "for future use" branches

### Leaked External Field Names
- An upstream API's or third-party schema's naming used as the project's domain vocabulary
- Raw response shapes threaded through core logic instead of mapping to the ubiquitous language at the boundary

### End-to-End-Only Testability
- Logic that can only be exercised through the full stack because effects weren't separated from computation
- Business rules buried inside I/O so they need a DB/network to test

### Over-Defensive Checks
- Null/None/type checks on values the types already guarantee are present and correct
- Try/except wrapping code that cannot throw, or re-validating data already validated at the boundary

## How to report

For each finding: `file:line`, the smell, **severity** (debt / friction / nit), and the fix — name the domain type to introduce, the existing abstraction to reuse, the speculative code to delete, the boundary mapping to add, the pure core to extract, or the redundant check to remove. NEVER auto-apply a change.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
