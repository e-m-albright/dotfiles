---
name: planning
description: This repo owner's pre-code scope-and-judgment criteria — should-we-build-this, define non-goals and "done", one-way vs two-way doors, complexity budget, a named red-flag list, plus execution discipline (standing refactor license, don't-overengineer-before-core, multi-pass cadence, operational simplicity while strapped). Use when deciding whether/how to build something and you want THIS take — "should we build this", "what's the smallest version", "what are the non-goals", "scope this", "is this a one-way door", "am I overengineering", "what are the red flags here", "is this worth it". Complements superpowers:writing-plans (which produces a step-by-step implementation plan); reach for this for the upstream scope/effort/reversibility judgment that decides what — and whether — to plan at all.
metadata:
  source: Promoted from the retired .ai/rules/process/planning.mdc; this skill is now the canonical home for that content.
---

# Planning & Scope

Apply these criteria during brainstorming, planning, and spec review — before writing code. By the time you're reviewing a PR, you've already committed to building the thing. These questions prevent building the wrong thing.

## When to Use

- Deciding whether something is worth building, and if so, what the smallest valuable version is.
- Scoping a task: defining "done", non-goals, increments, blast radius, rollback.
- Choosing between approaches on effort / reversibility / complexity / maintenance grounds.

**When NOT to use:**
- **`superpowers:writing-plans`** — when the *what* and *whether* are settled and you need a concrete, step-by-step implementation plan. That skill writes the plan; this one decides what (and whether) to plan.
- **`collaborative-ideation`** — when you want adversarial critique of an idea rather than scope/effort triage. The two pair well: ideate to pressure-test, then plan to scope.

## Should We Build This?

- Does this solve the user's real problem, or just the stated requirement? (ask why, not just what)
- Is this already available as a library, service, or built-in feature?
- What's the effort/impact ratio? (a 2-day feature 80% of users need vs. a 2-week feature for 5%)
- Will this compound? (platform features that enable future work > one-off solutions)
- Are we building optionality or lock-in? (prefer reversible decisions)

## Scope Check

- Is "done" clearly defined? (observable criteria, not open-ended exploration)
- What's the smallest version that delivers value? (the MVP of the feature, not the roadmap)
- What are we explicitly NOT building? (non-goals prevent scope creep)
- Can this be decomposed into shippable increments? (no 3-week branches with one big merge)
- Is this a one-way door or a two-way door? (one-way doors deserve more scrutiny — database schemas, public APIs, data deletion)

## Dependencies & Risk

- What are the blockers? (another team, a migration, an API change, a decision not yet made)
- What's the blast radius if this breaks? (how many users/systems affected?)
- What's the rollback plan? (feature flag, migration rollback, revert commit, or "hope"?)
- Are there deadlines, freezes, or releases this interacts with?
- Does this require coordinated deployment? (multiple services, database + code, config + code)

## Approach Selection

When choosing between approaches, evaluate:

- **Effort**: How long for a human? How long with AI assistance? (be honest about both)
- **Reversibility**: Can we change our minds later? At what cost?
- **Complexity budget**: Does this use up complexity budget on the right thing? (complexity in domain logic is justified; complexity in infrastructure is usually not)
- **Maintenance burden**: Who maintains this in 6 months? Is it obvious or does it require tribal knowledge?
- **Failure modes**: What happens when this goes wrong? Is the failure loud or silent?

When presenting options, include effort estimates for each and a clear recommendation with rationale. Don't present options without a recommendation — that's delegation, not advice.

## Red Flags

Stop and reconsider if you notice:
- The plan has no non-goals (scope will creep)
- "We'll figure that out later" on a load-bearing decision
- The approach requires everything to go right (no error paths planned)
- It's easier to describe what the code does than what problem it solves
- The estimate doesn't include testing, migration, or deployment time

## Execution Discipline

These are how the planning criteria above carry through into implementation. They're separate from "should we build it" because the failure modes are different — over-engineering and scope sprawl rather than misalignment.

### Standing license to refactor (when crossed in flight)

You have standing authorization to unify, remove duplication, and build better abstractions when you cross them in the course of other work. You do not need to ask permission for every refactor.

A refactor is **acceptable** if it:

- Aligns the implementation with the stated design or charter.
- Removes a real duplication or abstraction smell encountered on the way.
- Improves extensibility for already-planned work.
- Ships with the tests/observability the surrounding code already has.

A refactor is **not** acceptable if it:

- Breaks a contract surface without versioning.
- Expands scope mid-execution without an explicit re-brainstorm.
- Touches code outside the change's blast radius for aesthetic reasons.
- "Improves" something with no link to a stated goal.

When in doubt between a small patch and a clean rewrite, lean toward the rewrite, but propose it explicitly first. Architectural decisions still surface explicitly in design docs before code lands; the refactor license expands what is *allowed*, it does not remove the discipline of designing first.

### Don't overengineer before core works

If a feature feels like "such a waste of time right now," put it on the roadmap and move on. Pre-core polish and configurability is wasted effort — the core will change shape and invalidate the polish.

When implementing, ask "does the core experience work yet?" If not, defer nice-to-haves (theme picker, settings page, edge-case error states) to roadmap items. Focus on the critical path.

### Multi-pass cadence

Defer aggressively to downstream brainstorms. A closeout should surface gaps; it should not pre-resolve every gap. The operating mode is multiple discrete brainstorm-and-execute passes, not one giant pass.

Triage before asking. Not every gap surfaced needs an answer this turn. Carry it forward.

Defer a question to a later pass when:

- The answer is downstream of a decision that has not been made yet.
- The question is about an artifact that does not exist yet.
- Answering now would require fabricating context the user has not yet provided.

Do NOT defer when:

- The user has explicitly raised the question.
- Deferring would create a parallel-state smell (e.g., two design docs ship with conflicting vocabulary for the same concept). In that case the question is load-bearing for downstream coherence and must be answered.

Multi-pass is sequenced by exit criteria, not by calendar. "Multiple passes" does not mean "multiple weeks"; it means multiple discrete brainstorm-and-execute cycles.

### Operational simplicity while strapped

Pre-customer or resource-strapped projects should prefer script-level discipline over new infrastructure for safety properties. The safety net is harness-level discipline, not isolation infrastructure.

- Don't spin up a parallel env for safety properties when a one-line guard in a script does the job.
- Don't introduce IAM-locked credentials as a workflow step until external customers exist.
- Reuse existing surfaces (terminal UIs, existing CLIs) before building new ones.

Exceptions where infrastructure-level enforcement IS appropriate:

- External customers exist and a safety failure would be visible to them.
- The work is destructive by nature (database migrations, history rewrites, file deletions). Backups and review are mandatory regardless.
- The user explicitly asks for the architecturally rigorous path on a specific decision. Honour the instruction.

_Promoted from `.ai/rules/process/planning.mdc` (was an always-on rule; now an on-demand skill)._
