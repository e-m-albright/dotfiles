---
name: workflow-closeout-learning
description: Run an end-of-workflow closeout that audits testing coverage, extracts reusable learnings, and generates a clean new-chat bootstrap prompt. Use when the user asks to wrap up long work, formalize learnings, reduce context baggage, or start a fresh chat with strong context.
---

# Workflow Closeout Learning

Use this skill at the end of long workflows to capture value before context is lost.

## Required Outputs

Produce these outputs in order:

1. **Coverage posture check** across all requested surfaces:
   - unit
   - integration
   - end-to-end
   - smoke
   - front-end (Playwright / Cypress / Vitest browser mode)
   - user story or journey
2. **Learning artifacts** that formalize what was discovered.
3. **New chat bootstrap prompt** with minimal baggage and high signal.
4. **Automation proposals** (rules, docs, skills, tests) for repeatable improvement.

## Workflow

### 1) Audit test posture with evidence

For each test surface, report:

- current evidence (existing tests, commands, docs)
- confidence level (`high`, `medium`, `low`)
- gaps and concrete next actions

Use the project's existing test commands (`just test`, `npm test`, `pytest`, `cargo nextest run`, etc.). If the project ships an affected-files dispatcher (`just test auto`, Nx affected, Turborepo, etc.), use that and report which files it actually exercised.

If coverage is uncertain, say so directly and list what to inspect next.

### 2) Extract behavior learnings from the workflow

Capture reusable directives from user feedback and corrections:

- emphatic commands (`always`, `never`, `must`, `do not`)
- repeated preferences
- quality standards that changed outcomes
- prompts that produced better results

Normalize each learning into:

- `trigger` — what cue activates this rule
- `instruction` — the rule itself
- `scope` — `global`, `repo`, or `task-type`
- `strength` — `hard-rule` or `preference`
- `evidence` — short quoted snippet or paraphrase

### 3) Propose durable artifacts

Generate a concise artifact plan with file targets:

- specs: `docs/specs/` or `docs/roadmap/`
- test gaps: test file paths plus any affected-files manifest that needs updating
- skill updates: `.ai/skills/<skill-name>/SKILL.md`
- standards updates: `AGENTS.md` or `agents/shared/rules.md` (ask first for broad policy changes)
- memory updates: ask the user before promoting an in-session learning to global memory

Prefer additive changes that make future work discoverable by both humans and agents.

### 4) Create a new chat bootstrap prompt

Write a ready-to-paste prompt with these sections:

1. Goal and desired outcome
2. Current state (what is done)
3. Ground truth pointers (files, docs, tests)
4. Open risks and unanswered questions
5. Verification commands to run
6. First three actions for the new chat
7. Requested response format

Keep it short enough to be practical, but complete enough to avoid re-discovery work. A good bootstrap is ~200-400 words; longer than that and you've packed a chat history into a prompt.

## Response Template

Use this structure in closeout responses:

```markdown
## Closeout Audit
- Unit: ...
- Integration: ...
- End-to-end: ...
- Smoke: ...
- Front-end: ...
- User story/journey: ...

## Learning Artifacts
- Directive 1: trigger, instruction, scope, strength, evidence
- Directive 2: ...

## Recommended Formalization
- File/path change 1
- File/path change 2

## New Chat Bootstrap Prompt
<paste-ready prompt>
```

## Guardrails

- Do not claim test confidence without evidence.
- Separate facts from assumptions.
- If data is missing, propose the fastest path to collect it.
- Keep outputs operational, avoid abstract summaries.
- Pair with `session-closeout` discipline from `multi-agent.mdc` — close out the worktree verdict at the same time you produce the bootstrap.
