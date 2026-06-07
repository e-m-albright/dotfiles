---
name: form-align
description: The domain/ontology lens of the code-health portfolio — make the code reflect the business domain, using DDD's ubiquitous language, bounded contexts, and screaming architecture. Detects naming drift, leaked external field names, anemic models, mis-drawn context boundaries, and a directory tree that screams the framework instead of the domain. Use when the user says "align with the domain", "ubiquitous language", "bounded context", "this name doesn't match the business", "screaming architecture", "package by feature", "the code doesn't reflect the domain", or "fix the ontology". SKIP for behavior changes, bug-finding (/review), or purely mechanical refactors (form-tidy).
---

# Align

The **conceptual lens**: does the code speak the language of the domain? Structure can be clean and modules deep while the codebase still models the wrong concepts or names them after an external API. This lens aligns the code's vocabulary and boundaries with the domain — the backbone everything else hangs on, since names drive module boundaries.

It is *informed by and updates* the project's domain model. The full method (ubiquitous language → bounded contexts → package-by-feature → screaming architecture, plus the dependency-hierarchy enforcement) lives in [../converge/references/ONTOLOGY-AND-HIERARCHY.md](../converge/references/ONTOLOGY-AND-HIERARCHY.md) — read it; this skill is the conversational lens that applies it.

## When to reach for it

Names feel off, the same word means different things in different places, API/DB field names have leaked into the core, the top-level layout screams the framework (`controllers/`, `services/`), or a "module" spans two unrelated concepts. Conceptual misalignment, not mechanical mess.

## Process

1. **Extract the current vocabulary.** What concepts does the code name (types, modules, key functions)? List them.
2. **Compare to the domain glossary.** Read `CONTEXT.md`/`CONTEXT-MAP.md` (or `## Domain Language` in `AGENTS.md`) and ADRs. Find the drift:
   - **Leaked external names** — an API's or DB's field names used as domain vocabulary in the core. Map them at the boundary (anti-corruption), don't let them bleed inward.
   - **Polysemy** — one word meaning two things → that's a bounded-context seam; split the model, map between contexts, don't unify into mud.
   - **Missing/anemic concepts** — a real domain concept represented as loose primitives or a bag of data with no behavior.
   - **Framework-screaming layout** — top-level dirs naming the stack, not the domain; feature pieces scattered across layer folders.
3. **Propose renames and boundary moves** in the ubiquitous language. A deepened module is named for the concept it owns.
4. **Update the glossary inline.** Naming a concept not in `CONTEXT.md`? Add it (same discipline as `/grill-with-docs` — [../grill-with-docs/references/DOMAIN-FORMAT.md](../grill-with-docs/references/DOMAIN-FORMAT.md)). Sharpening a fuzzy term? Fix it there. The glossary is the durable artifact that makes the alignment stick.
5. **Ratchet structural wins into contracts.** Once a bounded context is cleanly separated, encode the layering/forbidden-import rule (import-linter / dependency-cruiser / ArchUnit) so it can't re-tangle — see ONTOLOGY-AND-HIERARCHY.md.

## Antagonists

- **vs `form-prune`/YAGNI:** DDD richness (value objects, aggregates, explicit boundaries) reads as ceremony to a minimalist. Tiebreak: **apply richness only in the core/complex subdomain; keep supporting and generic subdomains plain.** Don't model a CRUD table like an aggregate.
- **vs `form-deepen`:** mostly aligned — depth + domain naming reinforce each other. Conflict only if a "correct" boundary forces a shallow module; then prefer the deeper shape and reopen the boundary as an ADR.

When an alignment move contradicts a recorded ADR, surface it for reopening rather than re-litigating silently.

## Sources
- Evans, *Domain-Driven Design* (ubiquitous language, bounded contexts); Fowler, *BoundedContext*; Martin, *Screaming Architecture*; package-by-feature literature. Method detail and dependency-hierarchy enforcement in [ONTOLOGY-AND-HIERARCHY.md](../converge/references/ONTOLOGY-AND-HIERARCHY.md).
