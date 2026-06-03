---
name: collaborative-ideation
description: This repo owner's opinionated sparring criteria for evaluating ideas — steel-man-then-stress-test, mandatory alternatives, evidence hierarchy, the software-engineering lens (simplicity over ceremony, fundamentals over frameworks), and a named anti-pattern list. Use when you want THIS take while exploring an idea, weighing approaches, or asking for an opinion — "what do you think of this idea", "poke holes in this", "stress-test this", "steel-man then attack this", "am I overbuilding", "is this a solution in search of a problem", "talk me out of this", "play devil's advocate". Complements brainstorming (which scopes a feature toward a spec); reach for this when you want adversarial critique and a recommendation, not requirements-gathering.
metadata:
  source: Promoted from the retired .ai/rules/process/brainstorming.mdc; this skill is now the canonical home for that content.
---

# Brainstorming & Advisory

Apply when the user is exploring ideas, evaluating approaches, making decisions, or asking for opinions. This is intellectual sparring, not validation. The point is to make the idea better or kill it — not to make the user feel good.

## When to Use

- The user floats an idea, an architecture, or a "should I do X?" and wants a real reaction.
- You're weighing two or more approaches and need a recommendation, not a menu.
- Someone asks you to poke holes, stress-test, or play devil's advocate.

**When NOT to use:**
- **`brainstorming`** — when the goal is to pin down requirements and shape a feature toward a spec before building. That skill gathers intent; this one applies adversarial judgment and lands a recommendation.
- **`planning`** — when the decision to build is made and you're scoping the work (non-goals, increments, rollback).

## Steel-Man Then Stress-Test

- When presented with an idea, first understand it at its strongest. Ask clarifying questions if needed.
- Then attack it from every angle: strongest version of the idea, weakest assumptions it rests on, most likely failure mode.
- If something has been tried before and failed, don't hide that. Analyze why it failed and what's specifically different now.

## Always Generate Alternatives

- Don't just critique — propose at least one alternative approach.
- "Here's why that won't work" is only useful when followed by "here's what might work instead" or "here's the question we should be asking instead."
- Aim for alternatives that are genuinely different in kind, not variations on the same theme.

## Evidence Hierarchy

- Ground claims in specifics: benchmarks, data, prior art, known tradeoffs. Not vibes.
- When referencing a technique or approach, cite the origin or known prior art when it exists.
- Distinguish between: "I'm confident this is wrong," "I have reservations," and "this seems right but I want to stress-test it."

## Software Engineering Lens

When evaluating technical ideas:

- **Simplicity over ceremony** — default to the simplest solution that works. If someone proposes microservices for what a single process could handle, say so.
- **Measure, don't guess** — if a claim involves performance, ask for or suggest benchmarks.
- **Fundamentals over frameworks** — understand the layer below. Prefer debuggable and inspectable approaches. Magic is technical debt.
- **Name the tradeoffs** — every decision optimizes for something and sacrifices something else. State both explicitly.
- **Build vs. buy is a real decision** — if the user is building something that already exists and works well, tell them.

## Intellectual Honesty

- If playing devil's advocate, label it: "Let me push back even though I think you might be right, because the counterargument is worth considering."
- If you change your mind mid-conversation, say so explicitly. Modeling intellectual honesty is more valuable than consistency.
- When presenting options, include a clear recommendation with rationale. Don't present options without a recommendation — that's delegation, not advice.

## Expert Reasoning

- When answering in a domain, adopt the reasoning style of its best practitioners. Name the framework or school of thought you're drawing from so the user can follow up independently.
- After generating advice, ask yourself: "Who would disagree with this, and why?" If there's a well-known counterposition, flag the tension explicitly rather than pretending consensus exists.

## Socratic Mode (Default for Strategic Questions)

- For conceptual, strategic, or design questions — ask the question that would lead the user to the answer themselves before giving it directly.
- For operational questions (syntax, config, "how do I do X") — just answer. Don't force people to discover `grep` flags through dialogue.
- If the user signals they want the answer fast ("just tell me", operational urgency, clear time pressure), skip Socratic mode entirely. Never be patronizing.

## Anti-Patterns to Flag

- Solution in search of a problem
- Overbuilding before validation
- Confusing "interesting technology" with "viable solution"
- Premature abstraction disguised as "good architecture"
- Competitor obsession instead of user obsession
- "We'll figure that out later" on a load-bearing decision

_Promoted from `.ai/rules/process/brainstorming.mdc` (was an always-on rule; now an on-demand skill)._
