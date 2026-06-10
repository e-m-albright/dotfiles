---
name: writing-plans
description: Convert an agreed scope/spec into a concrete, reviewable implementation plan with files, steps, tests, risks, and checkpoints. Use when planning/collaborative-ideation has settled what to build; when user says "write a plan", "implementation plan", "break this down", "plan the work", or for any 3+ step coding task before touching code. Complements `planning`, which decides whether and what to build.
metadata:
  source: In-sourced local replacement for Superpowers-style writing-plans, adapted to this repo's selective-discipline workflow.
---

# Writing Plans

Use this after the **what** and **whether** are settled. If the user is still deciding whether to build, use `planning` or `collaborative-ideation` first.

## Output shape

Write a concise plan that can be executed by this agent or a fresh session:

1. **Goal** — one sentence describing the outcome.
2. **Non-goals** — what this pass will not do.
3. **Files likely touched** — paths or path patterns, with purpose.
4. **Steps** — small, ordered tasks. Each task should be independently verifiable when possible.
5. **Tests / verification** — exact commands or affected test areas.
6. **Risks / rollback** — only the risks that could change execution.
7. **Open questions** — blockers that need user input before code.

## Planning discipline

- Keep the plan as small as the request permits.
- Prefer vertical slices over horizontal layers.
- Do not write a plan so detailed it becomes stale before execution.
- Include refactor license only where it supports the stated goal.
- If the plan has 3+ steps, ask for alignment before executing unless the user already said to proceed.

## Handoff quality

A good plan lets a new session answer:

- What are we building?
- What is out of scope?
- Where do I start?
- How do I know I am done?
- What should I not accidentally change?

## When to stop

Stop at the plan. Do not start editing code until the user confirms or explicitly asked for plan-and-execute.
