---
name: form-clarify
description: The readability/interpretability lens of the code-health portfolio — make code understandable to a newcomer (and navigable by an agent), treating readability as its own dimension distinct from structure. Improves identifier quality, comment-code coherence, comments that explain the why, flow flatness, and structural indexes. Use when the user says "make this readable", "this is hard to follow", "improve naming", "is this interpretable / legible", "document the why", "make it newcomer-friendly", or "optimize for agent/LLM navigability". SKIP for behavior changes, bug-finding (/review), or pure deletion (form-prune).
---

# Clarify

> **Canon** — serves readability as a first-class dimension (graded by the review rubric); the why-comment rule of the kernel. See [ENGINEERING.md](../../../ENGINEERING.md).

The **interpretability lens**. Readability is a real, measured dimension — separate from module structure — and the literature splits it cleanly: a **structural** axis (line length, nesting depth, blank-line rhythm, identifier counts; Buse & Weimer) and a **textual** axis (identifier specificity, comment-code consistency, comment quality, textual coherence; Scalabrino). Both matter; either alone is insufficient. This lens improves both.

The hard caveat first: **no readability score is a target.** No automated metric correlates well with human understandability (Scalabrino et al., ASE'17), so use any score as a smell-detector that points you at a spot — never as a number to optimize. The judge is "would a competent newcomer understand this without spelunking?"

## When to reach for it

The code works and is reasonably structured, but a reader (human or agent) has to hold too much in their head, chase bad names, or reverse-engineer intent. This is about comprehension, not correctness or architecture.

## Process

1. **Find the hard-to-read spots.** Long mixed-boolean conditions, deep nesting, cryptic or generic identifiers (`data`, `tmp`, `handle`), comments that restate the code or have drifted from it, missing "why."
2. **Fix names first** — the highest-leverage readability move. Names should be specific to the domain (lean on the ubiquitous language; coordinate with `form-align`). A precise name deletes the need for a comment.
3. **Add comments that explain the why, not the what.** Per Ousterhout (and against Clean Code's "comments are failures"): comment the non-obvious — invariants, the reason for an odd choice, what a caller must know that the types don't say. Delete comments that narrate obvious code (that's slop, hand it to `form-prune`).
4. **Flatten flow** so it reads top-to-bottom: guard clauses over nesting, decompose tangled booleans into named predicates (coordinate with `form-tidy` for the mechanical transform).
5. **Add structural indexes for navigation** — a module docstring/header that says what's here and where, a barrel/`__all__`, a short ARCHITECTURE note for a package. This is what makes a codebase navigable to an agent.

## The human-vs-agent legibility tension (name it, don't merge it)

Human and machine readability overlap on the essentials — clear names, explicit types, coherent boundaries, tests — but **diverge on density**: humans want short files and whitespace for scanning; agents navigate better with *semantic density, consolidated context, explicit types, and structural indexes*. When they conflict, decide consciously per audience and record the call. Don't silently optimize one and degrade the other.

## Antagonists

- **vs `form-prune`:** comments and structural indexes add lines; minimalism cuts them. Tiebreak: keep the *why* and the navigation aids; cut redundant restating.
- **vs `form-deepen`/Clean-Code:** the "are comments good?" debate. Adopt Ousterhout — comments are essential for the non-obvious, useless when they echo code.
- **vs `form-tidy`:** a mechanically-cleaner transform can read worse; readability wins ties here.

## Sources
- Buse & Weimer, *A Metric for Software Readability* (ISSTA'08 / TSE'10); Scalabrino et al., *A Comprehensive Model for Code Readability* (JSEP'18) and *Automatically Assessing Code Understandability* (ASE'17, the "no metric is a target" caveat); Ousterhout, *A Philosophy of Software Design* (comments for the why); the human-vs-agent legibility split from current practitioner work on AI-legible codebases.
