# AI Coding Frameworks — Design Notes

> **Last reviewed**: 2026-04-17 — Tentative designs for our own agent workflow system.
> These are investigation notes, not a shipped framework.

---

## What Exists

Three major meta-frameworks constrain different aspects of the AI coding loop:

| Framework | Constrains | Philosophy | Stars | Install |
|-----------|-----------|------------|-------|---------|
| **Superpowers** | Development *process* | Iron laws, mandatory gates (TDD, verification, brainstorm-before-build) | ~15k | Claude Code plugin |
| **GSD (Get Shit Done)** | *Execution environment* | Context management, autonomous task sequencing, crash recovery | ~35k | Standalone TS CLI (v2 on Pi SDK) |
| **OMC (oh-my-claudecode)** | *Multi-agent orchestration* | 32+ specialized agents, autopilot/swarm modes, natural language commands | ~12k | npm package |

### What Each Gets Right

**Superpowers** — The iron laws are genuinely valuable:
- No production code without a failing test
- No fixes without root cause investigation
- No completion claims without verification evidence
- Brainstorm → plan → implement pipeline prevents "just code it" drift

**GSD v2** — Solves the real problem: context rot.
- Programmatic context management (clears between tasks, injects only what's needed)
- Autonomous milestone advancement without human babysitting
- Crash recovery and cost tracking
- Standalone CLI means it controls the harness, not the other way around

**OMC** — Multi-agent coordination at scale.
- 32 specialized agents with distinct roles
- Autopilot mode for autonomous execution
- Swarm mode for parallel agent orchestration
- Zero-config setup

### What Each Gets Wrong (Community Feedback)

**Superpowers**:
- "Shockingly verbose" — burns tokens on ceremony
- Every task triggers the full pipeline even when unnecessary
- The 1% rule ("even 1% chance = must invoke") compounds cost
- Multiple experienced devs say: use as a learning template, then build your own

**GSD**:
- v2 requires a separate CLI (not native to Claude Code plugin system)
- Opinionated about git workflow — may conflict with your own
- Less focus on code quality gates (no TDD enforcement)

**OMC**:
- Complexity overhead — 32 agents is a lot to reason about
- "Oh-My-Zsh syndrome" — easy to install everything, hard to know what's running
- Less battle-tested than Superpowers for disciplined workflows

---

## Our Design Goals

Based on Reddit thread feedback, community patterns, and our own experience:

### 1. Selective Discipline, Not Universal Ceremony

The #1 complaint about Superpowers is that it fires on everything. Our system should:
- **Distinguish task sizes**: a one-line fix doesn't need brainstorming → planning → worktrees
- **Gate on complexity, not existence**: only trigger multi-step workflows when the task actually has multiple steps
- **Keep iron laws, lose the verbosity**: TDD, root cause investigation, and verification are worth keeping. Design docs and 8-agent review panels are not always worth the tokens.

### 2. Context Budget Awareness

The Reddit thread's strongest tip: keep context under 250K tokens. 1M is a "noob trap."
- **Fresh subagents per task** (Superpowers does this well)
- **Explicit context injection** (GSD v2 does this well — only inject what's needed)
- **No accumulating design docs in the main context** — write to files, read when needed

### 3. Cross-Model Review

The emerging power pattern from multiple experienced devs:
- Claude writes code → Codex reviews it → Claude critiques the review
- Different models catch different classes of bugs
- Sonnet reviewer + Opus reviewer catch different things than Opus alone
- The Codex plugin for Claude Code (`/codex:review`) makes this trivial

### 4. Architecture Guardrails

Claude's biggest weakness per the thread: "hacks, patches, helper function sprawl instead of revisiting architecture." Fix with:
- **Architect review agent** that checks every changeset for SOLID, KISS, Clean Architecture
- **"Stop when tests break" directive** — don't blindly fix, stop and prompt
- **Anti-god-class rule** — if a file exceeds N lines or a function exceeds M lines, flag it

### 5. Portable Across Tools

Skills are just markdown files. They should work across Claude Code and Codex with minimal conversion.
- Keep skill instructions model-agnostic where possible
- Use `AGENTS.md` (read by both) for shared directives
- Tool-specific behavior in tool-specific files only

---

## Tentative Skill Set

A minimal, opinionated set — not 40+ skills, but the 6-8 that actually matter:

### Always On (process guardrails in CLAUDE.md / AGENTS.md)

```
- Stop when tests break — don't blindly fix them
- Keep context under 250K tokens
- No god classes (>300 lines = split)
- No helper function sprawl (>3 helpers in one file = refactor)
- Verify before claiming done (run tests, show output)
```

### Skills (invoke when needed)

| Skill | When | What It Does | Inspiration |
|-------|------|-------------|-------------|
| **plan** | 3+ step tasks | Interview-me questions → concise plan with file paths and verification steps | Superpowers writing-plans (lighter) |
| **tdd** | Adding logic or fixing bugs | RED → GREEN → REFACTOR cycle, no production code without failing test | Superpowers TDD (keep iron law, lose verbosity) |
| **debug** | Test failures, unexpected behavior | Reproduce → hypothesis → test hypothesis → fix. No shotgun fixes. | Superpowers systematic-debugging |
| **review** | After implementation | Dispatch reviewer subagent (or cross-model via Codex plugin) | Superpowers code-reviewer + cross-model pattern |
| **architect** | Changesets touching 3+ files | Check for SOLID violations, god classes, abstraction leaks | Reddit u/Ok_Age_390 pattern |
| **ship** | Ready to commit/PR | Verify tests → summarize changes → commit or PR | Superpowers finishing-a-development-branch (lighter) |

### What We Deliberately Skip

| Superpowers Skill | Why Skip |
|-------------------|----------|
| brainstorming (full Socratic process) | Overkill for most tasks. Replace with `plan` interview questions |
| writing-skills | Meta — only needed when writing new skills |
| using-git-worktrees | Just use worktrees directly, don't need a skill for it |
| dispatching-parallel-agents | The agent already knows how to dispatch subagents |
| receiving-code-review | Good principles, but enforced via AGENTS.md directives instead |
| executing-plans | Plans should be simple enough to just... execute |

---

## Implementation Notes

### Option A: Pure CLAUDE.md + Lightweight Skills

Simplest approach. Put guardrails in CLAUDE.md, create 4-6 skill markdown files, done.
- **Pro**: Zero dependencies, works today, portable to Codex
- **Con**: No programmatic context management (GSD's strength)

### Option B: Claude Code Plugin

Package skills as a Claude Code plugin (like Superpowers).
- **Pro**: Installable, versioned, shareable
- **Con**: Plugin ecosystem is young, more maintenance

### Option C: Standalone CLI (GSD v2 approach)

Build a wrapper CLI that manages context, dispatches tasks, tracks cost.
- **Pro**: Full control over context budget, crash recovery
- **Con**: Highest complexity, separate tool to maintain

**Recommendation**: Start with Option A. Graduate to Option B if the skills stabilize and we want to share them. Option C only if context management becomes a real bottleneck.

---

## Cross-Model Workflow Design

The most impactful pattern from the Reddit thread:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Claude Code │────▶│ Codex Review │────▶│ Claude Code │
│ (implement) │     │ (critique)   │     │ (address)   │
└─────────────┘     └──────────────┘     └─────────────┘
```

**Tools that enable this today**:
- Codex plugin for Claude Code: `/codex:review`, `/codex:adversarial-review`
- MCP server wrapping Codex CLI (community-built)
- "Baton-pass" handoffs: save state to `save-state.md` + `next-task.md`

**Our approach**: Use the Codex plugin for post-implementation review. Add to the `review` skill as an optional step.

---

## References

- Reddit thread: r/ClaudeCode "Claude Code (~100 hours) vs Codex (~20 hours)"
- Superpowers: Claude Code plugin (v5.0.7)
- GSD: https://github.com/gsd-build/get-shit-done | https://github.com/gsd-build/gsd-2
- OMC: https://github.com/Yeachan-Heo/oh-my-claudecode
- See also: `prompts/guides/ai-tools.md` (tool landscape), `prompts/guides/prompt-tactics.md` (prompt engineering)
