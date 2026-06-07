---
name: form-deepen
description: The taste-driven, conversational pole of the code-health portfolio — surface architectural friction and propose deepening opportunities that turn shallow modules into deep ones, then grill the design with the user. No metrics, no ratchet; pure judgment about depth, locality, and leverage. Use when the user wants to "deepen modules", "de-slop this module", "this feels coupled", "find the seams", "make this more testable / AI-navigable", "improve the design here", or wants to think through one area's architecture conversationally. SKIP for whole-repo measurable convergence, LOC ratchets, or static grading — that is converge; for a pre-merge diff review use /review.
metadata:
  source_url: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md
  source_commit: 733d312884b3878a9a9cff693c5886943753a741
  ported_at: 2026-05-07
  adaptations: Faithful replication of the upstream conversational deepening skill, kept deliberately minimal as the taste/divergent pole of the code-health skill portfolio (the measured whole-repo convergence engine lives in converge). Shared vocabulary references point to that skill rather than duplicating LANGUAGE.md / DEEPENING.md / INTERFACE-DESIGN.md.
---

# Deepen

> **Canon** — enacts Principle 5 (*Simplicity is the goal — small files are a proxy*): deep modules over shallow. See [CANON.md](../../../CANON.md).

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability, found by *judgment*, not measured by a gate.

This is the **taste pole** of the code-health portfolio: it ideates freely on improvements that are about design feel — depth, naming, the right seam — and that no metric can see. It pairs with [converge](../converge/SKILL.md) (the measured convergence engine): use this to *find* the deep move conversationally; use that to *measure, ratchet, and lock in* changes across a whole repo. Safety is still verified by tests; "better" here is gated by your judgment and the user's, and recorded as an ADR — not by a number.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [../converge/references/LANGUAGE.md](../converge/references/LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Key principles (see [../converge/references/LANGUAGE.md](../converge/references/LANGUAGE.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; ADRs record decisions the skill should not re-litigate.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs in the area you're touching first. The glossary may be a standalone `CONTEXT.md`/`CONTEXT-MAP.md`, or — for a small domain — a `## Domain Language` section inside `AGENTS.md`. Check both. (When you add a term and the inline section outgrows ~30 lines or a second bounded context appears, graduate it to a standalone `CONTEXT.md` and leave a pointer in `AGENTS.md`.)

Then use the Agent tool with `subagent_type=Explore` to walk the codebase. Don't follow rigid heuristics — explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and also in how tests would improve

**Use CONTEXT.md vocabulary for the domain, and [../converge/references/LANGUAGE.md](../converge/references/LANGUAGE.md) vocabulary for the architecture.** If `CONTEXT.md` defines "Order," talk about "the Order intake module" — not "the FooBarHandler," and not "the Order service."

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly (e.g. _"contradicts ADR-0007 — but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### 3. Grilling loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `CONTEXT.md`?** Add the term to `CONTEXT.md` — same discipline as `/grill-with-docs` (see [../grill-with-docs/references/DOMAIN-FORMAT.md](../grill-with-docs/references/DOMAIN-FORMAT.md)). Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `CONTEXT.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing — skip ephemeral reasons ("not worth it right now") and self-evident ones. See [../grill-with-docs/references/ADR-FORMAT.md](../grill-with-docs/references/ADR-FORMAT.md). This ADR is also how the *taste* decision becomes durable — it stops the measured engine (or a future pass) re-proposing what you deliberately rejected.
- **Want to explore alternative interfaces for the deepened module?** See [../converge/references/INTERFACE-DESIGN.md](../converge/references/INTERFACE-DESIGN.md). Deepening mechanics and dependency categories: [../converge/references/DEEPENING.md](../converge/references/DEEPENING.md).

## Sources
- Adapted from [mattpocock/skills/engineering/improve-codebase-architecture](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/improve-codebase-architecture/SKILL.md) (ported 2026-05-07, MIT). This is the faithful conversational original, retained as the taste pole of the portfolio; the measured convergence engine that grew out of it lives in [converge](../converge/SKILL.md).
