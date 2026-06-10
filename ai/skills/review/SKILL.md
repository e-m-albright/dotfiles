---
name: review
description: Pre-merge review of a diff, branch, PR, or chunk of work that fans out parallelizable audit threads (correctness, security, data-integrity, operations, plus a health rubric), then synthesizes them into one verdict — fix-first bug hunt (auto-fix the mechanical, flag the judgment calls) PLUS a letter-graded health report card. Use when the user says "review this PR/branch/diff", "review before merge", "is this safe to merge/ship", "what could break", "audit this change", "code review", "grade this PR", or wants a focused pass over a change about to land. NOT for chasing a known failing test (use systematic-debugging) and NOT for a dedicated exhaustive security-only audit (use security-review).
allowed-tools: Read Grep Glob Bash(git:*) Bash(gh:*) Bash(rg:*) Bash(wc:*) Agent
metadata:
  source: Merged from premerge-review (fix-first bug hunt) and code-quality-audit (graded health rubric). Criteria live in references/bug-hunt-criteria.md and references/health-rubric.md.
  note: Named review (not code-review) to avoid shadowing Claude Code's /code-review plugin command that `ccr` drives.
---

# Review

Two complementary lenses on the same change, run together before it merges:

1. **Bug hunt** — find defects about to land (correctness, security, data integrity, ops), then classify each finding fix-first: auto-fix the mechanical, flag the judgment calls.
2. **Health report card** — grade module health against the universal engineering rubric (letter grades + domain observations).

Fan the audit threads out in parallel, synthesize, then report both the fixed/flagged findings and the graded report card.

## When to Use

- Reviewing your own branch before opening a PR, or a teammate's PR before approving
- "Is this safe to ship?" / "what could break here?" / "review this diff" / "grade this PR"
- A final pass after `test-driven-development` / feature work, before PR/merge closeout
- Periodic health check on a module or directory (run the rubric threads, skip the diff-scoped ones)

**When NOT to use:**
- **`systematic-debugging`** — when something is *already* broken and you need the root cause. This skill reviews changes that (as far as anyone knows) work.
- **`security-review`** — when you want a dedicated, exhaustive security audit. This skill covers high-frequency security misses inline; a security-only deep dive is its own pass.

## Workflow

### 1. Establish scope

Determine exactly what you're reviewing and read it in full plus enough surrounding code to judge correctness — never review hunks blind:

- A PR number/URL → `gh pr diff <n>` (and `gh pr view <n>` for intent)
- The current branch → `git fetch origin && git diff origin/main...HEAD`
- Staged/working changes → `git diff` / `git diff --staged`
- A module/directory health check → read every file in scope, not just samples

If no scope is given, default to the unstaged changes (`git diff`).

### 2. Understand intent before judging

What is this change *trying* to do? Read the PR description / commit messages / linked issue. A correct implementation of the wrong thing is the most expensive bug.

### 3. Detect the surface(s)

By file extension and layout, so the right rubric criteria apply (see [Health rubric](references/health-rubric.md)):
- `*.py` / pyproject.toml → Python
- `*.rs` / Cargo.toml → Rust
- `*.ts`, `*.tsx`, `*.svelte`, `*.vue` → Web
- `*.go` / go.mod → Go
- Mixed → audit each surface separately, combine into one report

Read the philosophy first if present: `docs/engineering-philosophy.md` (project-local), else `~/.claude/rules/process/style-principles.md`. Then any `.ai/rules/process/*.mdc`, then surface rules under `.ai/rules/languages/` and `.ai/rules/frameworks/`. If the project has its own `code-health-manifesto.md` or equivalent, prefer it — projects own their philosophy.

### 4. Fan out the audit threads (parallelize)

Dispatch these independent threads — on Claude Code via the **Agent tool** (`subagent_type=Explore`), one per thread; otherwise walk them sequentially. Each thread gets the scope, the surface, and a pointer to its criteria. They have no shared state, so they run in parallel cleanly (see `dispatching-parallel-agents`).

| # | Thread | Lens | Criteria |
|---|--------|------|----------|
| **T1** | **Correctness** | bug hunt | [bug-hunt-criteria.md](references/bug-hunt-criteria.md) → Correctness |
| **T2** | **Security** | bug hunt | [bug-hunt-criteria.md](references/bug-hunt-criteria.md) → Security |
| **T3** | **Data Integrity** | bug hunt | [bug-hunt-criteria.md](references/bug-hunt-criteria.md) → Data Integrity |
| **T4** | **Operational Readiness** | bug hunt | [bug-hunt-criteria.md](references/bug-hunt-criteria.md) → Operational |
| **T5** | **Health — universal** | report card | [health-rubric.md](references/health-rubric.md) → U1–U11 |
| **T6** | **Health — surface + structure** | report card | [health-rubric.md](references/health-rubric.md) → surface criteria + anti-pattern scan |

Each thread returns its findings (bug-hunt) or its graded criteria (report card) with `file:line` evidence. Don't let a thread manufacture issues to look thorough — empty is a valid result.

### 5. Synthesize

Collect all threads. De-duplicate overlapping findings (a missing null guard may surface in both T1 and T5 — report it once, in the bug hunt, and let it cost the rubric grade). Reconcile severities. Compute the report-card grades and weighted overall.

### 6. Classify the bug-hunt findings fix-first

Every T1–T4 finding gets classified before reporting:

| Classification | Action | Criteria |
|---------------|--------|----------|
| **AUTO-FIX** | Fix silently | A senior engineer would apply without discussion. Mechanical, unambiguous. |
| **ASK** | Report and recommend | Reasonable engineers could disagree. Trade-offs, architecture, judgment. |

**AUTO-FIX** (just fix it): unused imports/variables, dead code, import ordering, formatting/naming inconsistencies with surrounding code, missing error context in log statements, obvious null guards at system boundaries, a deprecated API with a drop-in replacement.

**ASK** (report, don't touch): architectural changes (new abstractions, data flow), security-sensitive changes (auth, validation, secrets), API surface changes (new endpoints, changed contracts), dependency additions/removals, test strategy decisions.

**Default to ASK when uncertain.** Never make a judgment-call change silently. For the full table and worked examples, see [bug-hunt-criteria.md](references/bug-hunt-criteria.md).

### 7. Apply AUTO-FIX items, then report

Report in the format below.

## Output Format

```markdown
# Review: [scope]

## Summary
[1-2 sentences: what the change does + overall read. Verdict: safe to merge / fix top items first / not yet.]

## Auto-Fixed
- [mechanical fixes already applied, with file:line]

## Findings (bug hunt)
### [SEVERITY] Finding title
**Category**: Correctness | Security | Data Integrity | Ops | Performance
**Location**: file:line
**Recommendation**: [specific action]
**Why**: [brief rationale]

## Health Report Card
**Surface:** [Python | Rust | Web | Go | Mixed]  **Overall Grade:** [A–F, weighted]

| # | Criterion | Grade | Justification (file:line) |
|---|-----------|-------|---------------------------|
| U1 | Type Safety | B+ | ... |
| ... | ... | ... | ... |

### Domain Observations
- **Strength / Opportunity / Concern:** [title] — [1-3 sentences, file:line]

## Top 3 Action Items
1. **[Priority]** [action + file:line] — [why it matters]
2. ...
3. ...
```

Severity: **Critical** (must fix before merge), **Warning** (should fix), **Note** (consider).

Below a **B** overall should not merge without addressing the top action items. If there are no findings, say so plainly — don't manufacture issues.

## Composition

On Claude Code, the `ccr` alias drives a multi-agent flow (`/review-pr` locally, `/code-review` plugin for PRs with GitHub comments). This skill is the single shared rubric those agents and any other vendor (Codex, Cursor, Pi) use — invoke it directly for one focused pass, or let it back the multi-agent orchestration. The thread fan-out in step 4 is itself a parallel-agent dispatch (see `dispatching-parallel-agents`).
