---
name: prune
description: The minimalism/deletion lens of the code-health portfolio — improve a codebase by removing rather than adding. Hunts dead code, speculative abstraction, unused flags/config, premature generality, redundant layers, and features nobody uses, then deletes them safely. The one lens with an honest hard metric — net LOC and feature count go down. Use when the user says "what can we delete", "this is over-engineered", "YAGNI", "remove dead code", "make it smaller", "simplify by removing", "trim this", or "prune". SKIP for diff-scoped quality cleanup (/simplify), bug-finding (/review), or adding structure (deepen/align).
---

# Subtract

The **deletion lens** — worse-is-better, YAGNI, "the best code is no code." Every other lens can add (abstraction, types, comments, structure); this one only asks **what can be removed without losing behavior the system actually needs?** It's the counterweight that keeps the portfolio from accreting, and it's grounded by the GitClear finding that AI assistants overwhelmingly *add* and rarely consolidate.

It is codebase-scoped and deletion-first — distinct from the built-in `/simplify` (which cleans the current diff) and from `tidy` (which restructures). Subtract's success metric is honest and visible: **net lines and surface area go down**, achieved by real removal, never by compressing or laundering (no comment-stripping — that's gaming, see [METRICS.md](../converge/references/METRICS.md)).

## When to reach for it

The code is bloated: defensive checks the types make impossible, abstractions with one caller, config knobs nobody sets, a base class with one subclass, layers that only pass through, two implementations of one concept, features behind a flag that's been off for a year.

## Process

1. **Find the removable.** Sweep for:
   - **Dead code** — unused exports/functions/imports, unreachable branches, commented-out blocks. Use `knip`/`vulture`/`ts-prune`/`cargo machete` where present.
   - **Speculative abstraction** — interfaces/factories/generics with a single concrete use (Rule of Three failures); inline them.
   - **Premature/unused config** — flags, options, env vars that are never varied; collapse to the one real value.
   - **Pass-through layers** — modules that only delegate (fail the deletion test); inline them.
   - **Competing versions** — `*V2`/`*_legacy`/shims kept "just in case"; delete the loser (no competing versions).
   - **Unused features** — behind dead flags or with no callers/usage; remove with the owner's confirmation.
2. **Confirm it's truly unused** before deleting — check call sites, dynamic dispatch, reflection, external consumers, and public API surface. A wrong deletion is a behavior change. Lean on the type system and a full test run.
3. **Delete in safe, reviewable steps**, each verified green; separate deletion commits (git keeps history — deleting confidently is the point).
4. **Report the pruneion** — LOC removed, surface area removed. This is the one place celebrating the number is legitimate, because it was earned by real removal.

## Antagonists

- **vs `deepen` / `align` / `purify`:** they add structure; you remove it. Tiebreak: **delete first, then deepen/model what genuinely remains** — it's cheaper to add structure to less code than to restructure code you were about to delete.
- **vs `clarify`:** comments and structural indexes are lines too. Tiebreak: keep the *why* comments and navigation aids; cut redundant restating and ceremony.
- **vs DRY:** sometimes the smallest code keeps a little duplication rather than a shared abstraction. Tiebreak: prefer duplication over the wrong abstraction (Metz); abstract only at the rule of three with a stable shape.

A deletion that reverses a recorded "keep this for reason X" ADR must be surfaced, not silently re-done.

## Sources
- Gall's Law / worse-is-better (Gabriel); YAGNI (Beck/XP); "best code is no code" (Welsh); Tigerstyle and Carmack-style simplification; Metz, *The Wrong Abstraction*; Dodds, *AHA Programming*. LOC-as-honest-proxy and anti-gaming in [METRICS.md](../converge/references/METRICS.md).
