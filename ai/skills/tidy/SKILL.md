---
name: tidy
description: The safe-execution lens of the code-health portfolio — apply named, behavior-preserving refactorings from the Fowler/Beck catalog (extract function, inline, guard clauses, replace conditional with polymorphism or lookup, decompose conditional, slide statements) in small two-hats steps, verified by tests, routed through deterministic codemods where possible. Use when the user says "tidy this", "clean up this function", "extract a method", "flatten these conditionals", "apply a refactoring", "this is messy", "guard clauses", or wants a known transform done safely. SKIP for whole-repo measured convergence (converge), conceptual design conversations (deepen), or bug-finding (/review).
---

# Tidy

The **mechanical, behavior-preserving execution lens** (Fowler's *Refactoring*, Beck's *Tidy First?*). Where `deepen` decides *what* design to pursue and `converge` *measures and ratchets* a whole repo, `tidy` is how you safely make a specific structural change *now*: pick a named transform, apply it in tiny steps, keep the tests green, commit it separately.

It's the most schedulable lens because the transforms are deterministic and behavior-preserving — but it's also the easiest to over-apply, so it carries explicit antagonist guards.

## When to reach for it

A specific piece of code is hard to read or change, you know roughly the shape you want, and the move is a named, safe transform — not an open design question. Diff- or function-scoped, not repo-wide.

## The two hats

Every edit is *either* a structure change *or* a behavior change, never both. Tidy only wears the **structure** hat: the code does exactly what it did before, organized better. If you discover a bug mid-tidy, stop, switch hats, fix it as its own commit, then resume. Mixing the two is how "refactors" smuggle in regressions.

## Process

1. **Name the smell and the transform.** Don't free-form. Map the smell to a catalog entry — the common ones, with the selection heuristic from [../converge/references/DE-SLOP.md](../converge/references/DE-SLOP.md):
   - deep nesting with early exits → **Replace Nested Conditional with Guard Clauses**
   - dispatch on a value/key → **Replace Conditional with Lookup/Table**
   - dispatch on a type/variant → **Replace Conditional with Polymorphism**
   - tangled boolean → **Decompose / Consolidate Conditional**, then Extract
   - a function doing several things → **Extract Function** (but mind the depth antagonist below)
   - a pass-through or speculative indirection → **Inline**
2. **Make the smallest step.** One transform, one place. A big tidy is a sequence of small ones, each independently green.
3. **Verify by test after each step.** Run the affected tests. Behavior preserved means the suite still passes — never judge by "the diff looks right." Tolerate a transient red mid-step, but return to green before committing.
4. **Route the rote bulk through codemods.** Renames, mechanical extractions, guard-clause flattening, dead-code removal: prefer `ast-grep` / `comby` / OpenRewrite where the pattern is regular — they're correct by construction. Reserve hand-editing for the judgment parts.
5. **Commit structure-only, separately.** Keep tidy commits out of feature commits so review and `git bisect` stay clean (Beck's separate-commits rule).

## Tidy first?

Tidy *before* a feature only when it makes that feature quicker, smaller, or safer to add — "make the change easy, then make the easy change." Over-tidying with no impending change is procrastination (Beck). If you're tidying for its own sake at repo scale, that's the `converge` loop's job, with a ratchet to make it converge.

## Antagonists (decide, don't let the last edit win)

- **vs `deepen` (Ousterhout):** aggressive Extract-Function can shatter a deep module into shallow ones with entangled interfaces ("lasagna code" — the documented Ousterhout-vs-Clean-Code tension). Tiebreak: **extract for a real seam or genuine reuse, not to hit a line target.** If the extracted pieces only ever call each other in order, you made it worse.
- **vs `prune`:** extracting duplication competes with deleting it. Tiebreak: if a caller can just *lose* the code, delete it (prune) before abstracting it (tidy).
- **vs `clarify`:** a transform that's mechanically cleaner can read worse. Tiebreak: if the named transform reduces readability, it's not a tidy — skip it.

When a tidy would reverse a decision recorded in the ADR log, stop and surface it rather than flip-flopping.

## Sources
- Fowler, *Refactoring* 2e (the catalog, small steps, separate commits); Beck, *Tidy First?* (two hats, tidy-first economics). Transform selection heuristic shared with [DE-SLOP.md](../converge/references/DE-SLOP.md).
