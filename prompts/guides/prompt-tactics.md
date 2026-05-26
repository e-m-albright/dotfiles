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

## Routine Prompts (Scheduled Automation)

Ready-to-use prompts for Claude Code Routines, Cursor Automations, or Codex Cloud.
These are designed for **supervised autonomy** — the agent does the work, you review the PR.

### Dependency Audit (Weekly)

```
Audit all dependencies for security vulnerabilities and outdated packages.

Steps:
1. Run the project's native audit command (cargo audit, npm audit, pip audit, etc.)
2. For each finding, assess severity (critical/high/medium/low)
3. For critical and high findings, check if an upgrade is available and whether it has breaking changes
4. Create a markdown report at .ai/artifacts/reports/dep-audit-YYYY-MM-DD.md with:
   - Summary table (package, current version, vulnerability, severity, fix available)
   - Recommended actions ranked by severity
   - Any findings that need manual investigation

Do NOT upgrade anything. Report only. If there are zero findings, still create the report confirming a clean audit.
```

### Stale Branch Cleanup (Weekly)

```
Clean up stale git branches in this repository.

Steps:
1. List all remote branches merged into main/master
2. List all remote branches with no commits in the last 30 days
3. For merged branches: delete them (except main, master, develop, staging, production)
4. For stale unmerged branches: list them in a report but do NOT delete
5. Create a summary: how many deleted, how many stale-but-kept, any anomalies

Never delete branches that are:
- Protected (main, master, develop, staging, production)
- Currently checked out by anyone
- Part of an open pull request
```

### Test Suite Health (Daily)

```
Run the full test suite and report on health.

Steps:
1. Detect the test runner (cargo test, pytest, vitest, jest, etc.)
2. Run the full suite, capturing output
3. Create a report at .ai/artifacts/reports/test-health-YYYY-MM-DD.md with:
   - Pass/fail/skip counts
   - List of failing tests with error messages
   - Any tests that are flaky (passed on retry but failed initially)
   - Test execution time (flag any test over 10 seconds)
   - Comparison to previous report if one exists (new failures, fixed tests)

Do NOT fix any tests. Report only. If all tests pass, confirm with the counts.
```

### Dead Code Detection (Monthly)

```
Scan for likely dead code in the codebase.

Steps:
1. Find exported functions/types that have zero import references outside their own file
2. Find files with no imports from anywhere in the project
3. Check for commented-out code blocks longer than 5 lines
4. Look for TODO/FIXME/HACK comments older than 6 months (check git blame dates)
5. Create a report at .ai/artifacts/reports/dead-code-YYYY-MM-DD.md with:
   - Likely dead exports (with file:line references)
   - Orphan files
   - Stale commented-out blocks
   - Aged TODOs

Confidence-rate each finding (high/medium/low). Do NOT delete anything.
Flag false-positive risks (e.g., exports used by external consumers, dynamic imports).
```

### README/Docs Drift Check (Weekly)

```
Check whether documentation matches the current codebase.

Steps:
1. Read README.md and any docs/ directory
2. For each documented command, API endpoint, or feature:
   - Verify the code it describes still exists
   - Check if function signatures or CLI flags have changed
   - Flag any documented behavior that no longer matches implementation
3. Scan for new public exports or commands that are NOT documented
4. Create a report at .ai/artifacts/reports/docs-drift-YYYY-MM-DD.md with:
   - Stale docs (references something that changed or was removed)
   - Missing docs (new features with no documentation)
   - Suggested fixes (brief, actionable)

If you are confident in a fix (e.g., a renamed flag), open a PR with the correction.
For ambiguous cases, report only — don't guess at intent.
```

### Cross-Model Code Review (On PR)

```
You are reviewing code that was written by a different AI model (Codex/GPT).
Review it as a staff engineer who assumes nothing about the author's competence.

For each file changed in this PR:
1. Check: Does the change match the PR description? Any scope creep?
2. Check: Are there tests for the new behavior? Do they test the right thing?
3. Check: Any security concerns (injection, auth bypass, data exposure)?
4. Check: Any performance concerns (O(n²), unbounded queries, missing indexes)?
5. Check: Does it follow existing project conventions (naming, error handling, file structure)?
6. Check: Any god classes, helper sprawl, or premature abstractions?

Rate each finding: Critical (must fix) / Important (should fix) / Suggestion (nice to have).
Only report Critical and Important findings. Skip nitpicks.
If the code is clean, say so — don't invent problems.
```

### Architecture Drift Check (Monthly)

```
Review the codebase for architectural drift and anti-patterns.

Steps:
1. Map the module/crate/package dependency graph
2. Flag circular dependencies
3. Find files over 500 lines — these are candidates for splitting
4. Find functions over 50 lines — these are candidates for refactoring
5. Check for SOLID violations:
   - Single Responsibility: files/modules doing too many things
   - Dependency Inversion: concrete types where interfaces should be
   - Open-Closed: switch statements that grow with every new variant
6. Check for layering violations (e.g., HTTP handler calling database directly)
7. Create a report at .ai/artifacts/reports/arch-review-YYYY-MM-DD.md with:
   - Dependency graph (text format)
   - Top 10 largest files with line counts
   - SOLID violations with file:line references
   - Recommended refactoring priorities (ranked by impact)

Do NOT refactor anything. Report only.
```

### Suggested Routine Schedule

| Routine | Schedule | Priority | Start With |
|---------|----------|----------|------------|
| Test suite health | Daily | High | Yes — lowest risk, highest signal |
| Dependency audit | Weekly (Monday) | High | Yes — security-critical |
| Docs drift check | Weekly (Wednesday) | Medium | After first two are stable |
| Stale branch cleanup | Weekly (Friday) | Medium | After first two are stable |
| Dead code detection | Monthly (1st) | Low | Once you trust the output format |
| Architecture drift | Monthly (15th) | Low | Once you trust the output format |
| Cross-model review | On PR | Medium | Set up as GitHub trigger |

> **Start with just two**: Test suite health (daily) and Dependency audit (weekly). Run them for two weeks. If the reports are useful and the noise is low, add more.

---

## References

- Reddit: r/ClaudeCode "Claude Code (~100 hours) vs Codex (~20 hours)" — community techniques
- See also: `prompts/guides/ai-coding-frameworks.md` (framework design), `prompts/guides/ai-tools.md` (tool landscape)
