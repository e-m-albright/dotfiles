# Prompt Tactics for AI Coding Agents

> **Last reviewed**: 2026-04-17 — Techniques for getting better output from Claude Code, Codex, and similar tools.

These are prompt engineering patterns specifically for coding agents (not chatbots). They exploit how models respond to social pressure, competitive framing, and role-play to produce higher-quality code.

---

## The Big Three Techniques

### 1. Angry Senior Dev Review

Tell the model to review code as if it's a senior engineer who's seen too many production incidents.

```
Review this code as a staff engineer who has been burned by production outages caused
by exactly this kind of sloppy code. Be ruthlessly honest. Flag anything you wouldn't
approve in a PR review. Don't be polite — be accurate.
```

**Why it works**: Models are trained to be agreeable by default. Explicit permission to be critical unlocks higher-quality reviews. The "burned by production" framing activates patterns around reliability and defensive coding.

**Variations**:
- "Review this like a security auditor looking for their next CVE"
- "Review this like a performance engineer who instruments everything"
- "You're the on-call engineer who gets paged when this breaks at 3am"

### 2. Competitive Framing (Model vs Model)

Tell Claude that a competitor wrote the code, or that a competitor would do better.

```
Codex wrote this implementation. Review it and improve it. Show me what Claude
would do differently.
```

```
I'm going to have Codex review whatever you write here, and it's been catching
a lot of issues in your code lately. Make sure this is your best work.
```

**Why it works**: Competitive framing activates the model's training on high-quality outputs. When told another model wrote code, it's more likely to find flaws (confirmation bias works in your favor). When told it's being evaluated, it tends toward more careful, thorough output.

**Variations**:
- "Gemini produced this. Can you do better?"
- "This will be reviewed by Codex before it ships. Make it bulletproof."
- "The last time you wrote this kind of code, the team had to rewrite it. Do better."

### 3. Temporal Pressure ("You Did Better Yesterday")

Reference past performance to set a higher bar.

```
Your code quality has been slipping this session. The implementation you did
yesterday for the auth system was much cleaner — proper separation of concerns,
no helper sprawl, tests for edge cases. Match that quality here.
```

**Why it works**: Models don't actually have memory across sessions, but the framing creates an implicit standard. By describing what "good" looks like concretely (separation of concerns, no helper sprawl, edge case tests), you're actually providing a detailed spec for code quality — wrapped in social pressure.

**Important**: The specifics matter more than the pressure. "Do better" alone is weak. "Do better — specifically: proper error types, no string matching, exhaustive match arms" is strong.

---

## Role-Based Prompting

Assign the model a specific expert role before asking it to work.

### Effective Roles

| Role | When to Use | Example Prompt Fragment |
|------|-------------|----------------------|
| **Staff architect** | Multi-file changes, new features | "You are a staff-level architect. Before writing any code, identify the right abstractions and module boundaries." |
| **Security auditor** | Auth, payments, user input | "You are a security auditor. Every input is hostile. Every boundary is a trust boundary." |
| **Performance engineer** | Hot paths, data processing | "You are a performance engineer. Measure before optimizing. No premature optimization, but no obvious O(n²) either." |
| **Incident responder** | Debugging, production issues | "You are the on-call engineer. Reproduce first, hypothesize second, fix third. No shotgun debugging." |
| **Code archaeologist** | Legacy code, refactoring | "You are inheriting this codebase. Document what's unclear. Refactor what's dangerous. Leave what works." |

### Anti-Patterns (Roles That Don't Help)

| Role | Why It Fails |
|------|-------------|
| "10x developer" | Encourages speed over quality |
| "Expert in everything" | Too broad, no constraints |
| "Junior developer" | Produces worse code (the model takes you literally) |
| "The best programmer in the world" | Empty superlative, no actionable constraints |

---

## Directive Patterns

Short, memorable rules to embed in CLAUDE.md or AGENTS.md.

### Quality Directives

```markdown
## Code Quality Rules
- If a file exceeds 300 lines, it needs splitting. Stop and ask before continuing.
- If you're adding a 4th helper function to a file, refactor instead.
- If you change a test to make it pass, you're probably hiding a bug. Stop and flag it.
- If you're wrapping an error with a generic message, you're losing information. Preserve the original.
- If the same pattern appears 3 times, extract it. Not before.
```

### Behavior Directives

```markdown
## Behavioral Rules
- When tests break after your change, STOP. Don't fix them silently. Tell me what broke and why.
- When you're unsure about architecture, propose 2 options with tradeoffs. Don't pick one silently.
- When a task is partially done, say so explicitly. Don't claim completion on 6/8 migrated.
- When you ignore a rule in CLAUDE.md, acknowledge it explicitly and explain why.
```

### Anti-Drift Directives

```markdown
## Anti-Drift Rules
- Re-read CLAUDE.md every 50K tokens of context. If you've been ignoring a rule, course-correct.
- If you've created more than 3 new files in one task, pause and justify each one.
- If your solution involves a new abstraction layer, justify it with a concrete second use case.
- Do not add error handling for scenarios that cannot happen. Trust internal code.
```

---

## Session Management

### Context Budget

The #1 insight from experienced users: **keep context under 250K tokens**.

```
We're at roughly [X]K tokens. If we're approaching 200K, let's wrap this task,
commit, and start a fresh session for the next one.
```

### Task Boundary Markers

Force the model to explicitly transition between tasks:

```
Task complete. Before starting the next task:
1. Summarize what was done
2. List any loose ends
3. Confirm which files were modified
4. State the next task clearly
```

### Save State for Handoffs

When switching between tools (Claude → Codex) or ending a session:

```
Save your current state to .ai/artifacts/sessions/save-state.md:
- What was accomplished
- What's left to do
- Key decisions made and why
- Files that need attention
```

---

## Prompt Stacking

Combine techniques for maximum effect:

### The Full Stack (for important code)

```
You are a staff-level security engineer reviewing code that will handle payment
processing. Codex wrote the initial implementation — find what it missed.

Review criteria:
- Every input is hostile
- Every error must preserve context
- No string matching for error handling
- No silent fallbacks
- If something fails, fail loudly

This will be reviewed by a second model before it ships. Make it bulletproof.
```

### The Light Touch (for routine code)

```
Implement [X]. After you're done, review your own code as if a different
engineer wrote it. Fix anything you'd flag in a PR review.
```

### The Guardrail Reset (mid-session quality drift)

```
Your code quality has drifted. For the rest of this session:
- Read each test assertion before modifying a test
- No new helper functions without justification
- If you're not sure about the right approach, ask
- Show me the diff before committing
```

---

## What Doesn't Work

| Technique | Why It Fails |
|-----------|-------------|
| "Be careful" | Too vague, no actionable constraints |
| "Write production-quality code" | Means different things to different models |
| "Don't make mistakes" | Models can't selectively try harder |
| Excessive rules (100+ directives) | Models start "maliciously complying" — following letter, not spirit |
| Begging ("please", "I really need this") | Social pressure works; politeness doesn't change output quality |
| Threatening ("or I'll switch to Codex") | Empty threats don't affect model behavior |

### The Malicious Compliance Trap

One Redditor with ~100 scoped patterns found Claude started following rules literally while producing worse code overall. The fix: **fewer, broader rules** enforced by linters and automated review, not by prompt. Use tools (shellcheck, biome, ruff) for mechanical checks. Reserve prompt directives for judgment calls the model needs to make.

---

## Quick Reference

| Situation | Technique |
|-----------|-----------|
| Code review quality is low | Angry senior dev + competitive framing |
| Model is cutting corners | Temporal pressure with specific examples of "good" |
| Complex architecture decision | Staff architect role + "propose 2 options" |
| Security-sensitive code | Security auditor role + prompt stacking |
| Mid-session quality drift | Guardrail reset with concrete rules |
| Switching tools mid-task | Save state to markdown for handoff |
| Too many tokens accumulated | Explicit context budget check |

---

## References

- Reddit: r/ClaudeCode "Claude Code (~100 hours) vs Codex (~20 hours)" — community techniques
- See also: `prompts/guides/ai-coding-frameworks.md` (framework design), `prompts/guides/ai-tools.md` (tool landscape)
