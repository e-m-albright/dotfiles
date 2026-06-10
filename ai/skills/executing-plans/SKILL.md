---
name: executing-plans
description: Execute an existing implementation plan with checkpoints, small verified steps, and no scope drift. Use when the user says "execute this plan", "work through the plan", "implement PLAN.md", or points to a written plan/spec that is ready to build.
metadata:
  source: In-sourced local replacement for Superpowers-style executing-plans, adapted to this repo's selective-discipline workflow.
---

# Executing Plans

Use this when a plan already exists and the task is to implement it, not redesign it.

## Before touching code

1. Read the plan/spec and identify the next concrete task.
2. Check current git state and relevant project instructions.
3. Confirm whether any open question blocks implementation.
4. Initialize or update the visible task tracker if the plan has multiple steps.

## Execution loop

For each task:

1. Mark the task in progress.
2. Make the smallest coherent change.
3. Run the narrowest relevant verification.
4. Mark complete only after verification or explicitly note why verification is deferred.
5. Summarize the delta before moving to the next task if the plan is long or risky.

## Scope control

- Do not silently expand scope beyond the plan.
- If implementation reveals the plan is wrong, stop and propose a plan amendment.
- Refactor only within the blast radius and only when it supports the plan.
- Preserve the user's chosen architecture unless evidence shows it is unsound.

## Checkpoints

Pause for user review when:

- A step changes public API, schema, data migration, auth, billing, or destructive behavior.
- Tests fail in a way not explained by the current change.
- The plan's assumptions are false.
- The next step would create a parallel implementation or compatibility layer.

## Completion

Before claiming done:

- Show verification commands and results.
- List remaining skipped/deferred tasks, if any.
- Call out docs/readme changes needed for user-facing behavior.
- Recommend review/PR/closeout only if the task is actually ready for that stage.
