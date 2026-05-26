---
name: premerge-review
description: Pre-merge bug-finding review of a diff, branch, or PR — hunts correctness, security, data-integrity, and operational defects, then classifies each finding fix-first (auto-fix the mechanical, flag the judgment calls). Use when the user says "review this change/diff/branch/PR", "review before merge", "what could break here", "is this safe to ship/merge", or wants a focused single-reviewer pass over a change about to land. NOT for letter-graded health report cards (use code-quality-audit) and NOT for chasing a known failing test (use diagnose/systematic-debugging).
allowed-tools: Read Grep Glob Bash(git:*) Bash(gh:*) Bash(rg:*) Bash(wc:*)
metadata:
  source: Derived from .ai/rules/process/code-review.mdc (the canonical rubric). Keep the two in sync; this skill is the invoked workflow, the rule is ambient guidance.
  note: Named premerge-review (not code-review) to avoid shadowing Claude Code's /code-review plugin command that `ccr` drives.
---

# Pre-Merge Review

Find the bugs in a change before it merges. Read the change against hard-won checklists, fix what a senior engineer would fix without discussion, and surface the rest as classified findings.

## When to Use

- Reviewing your own branch before opening a PR, or a teammate's PR before approving
- "Is this safe to ship?" / "what could break here?" / "review this diff"
- A final pass after `tdd-vertical-slices` / feature work, before `finishing-a-development-branch`

**When NOT to use:**
- **`code-quality-audit`** — when you want a graded report card on module *health* (letter grades, holistic), not a pre-merge bug hunt.
- **`diagnose` / `systematic-debugging`** — when something is *already* broken and you need to find the root cause. This skill reviews changes that (as far as anyone knows) work.
- **`security-review`** — when you want a dedicated, exhaustive security audit. This skill covers the high-frequency security misses inline, but a security-only deep dive is its own pass.

## Workflow

1. **Establish scope.** Determine exactly what you're reviewing:
   - A PR number/URL → `gh pr diff <n>` (and `gh pr view <n>` for intent)
   - The current branch → `git fetch origin && git diff origin/main...HEAD`
   - Staged/working changes → `git diff` / `git diff --staged`
   - Read the diff in full plus enough surrounding code to judge correctness. Don't review hunks blind.

2. **Understand intent before judging.** What is this change *trying* to do? Read the PR description / commit messages / linked issue. A correct implementation of the wrong thing is the most expensive bug.

3. **Pass over the checklists below.** For each file/hunk, walk the Correctness → Security → Data Integrity → Operational lenses. Note the non-obvious ones; the model is good at surface issues and bad at these.

4. **Classify every finding fix-first** (see below).

5. **Apply AUTO-FIX items**, then **report** in the output format.

## Fix-First Classification

Classify every finding before reporting:

| Classification | Action | Criteria |
|---------------|--------|----------|
| **AUTO-FIX** | Fix silently | A senior engineer would apply without discussion. Mechanical, unambiguous. |
| **ASK** | Report and recommend | Reasonable engineers could disagree. Trade-offs, architecture, judgment. |

**AUTO-FIX** (just fix it): unused imports/variables, dead code, import ordering, formatting/naming inconsistencies with surrounding code, missing error context in log statements, obvious null guards at system boundaries, a deprecated API with a drop-in replacement.

**ASK** (report, don't touch): architectural changes (new abstractions, data flow), security-sensitive changes (auth, validation, secrets), API surface changes (new endpoints, changed contracts), dependency additions/removals, test strategy decisions.

**Default to ASK when uncertain.** Batch ASK findings into the summary; never make a judgment-call change silently.

## Correctness (the non-obvious)

- **Race conditions** — shared mutable state, check-then-act, TOCTOU
- **Off-by-one** — fenceposts, inclusive vs. exclusive ranges, pagination boundaries
- **Floating-point for money** — use integers/decimals
- **Ordering assumptions** — async operations, event handlers, map iteration order
- **Type assertions lying about reality** — `as any`, unsafe casts, non-null `!` on nullable values
- **Error paths** — is the failure case handled, or only the happy path? Are errors swallowed?

## Security (what models routinely miss)

- **IDOR** — can a user reach another user's resource by changing an ID?
- **Timing-safe comparison** for secrets/tokens (constant-time equality)
- **ReDoS** — catastrophic backtracking on user-supplied regex input
- **Deserialization safety** on untrusted data
- **Response body filtering** — allowlists not blocklists for serialized fields (no leaking internal fields)
- **CORS** not `*` in production
- **Injection** — parameterized queries, escaped shell/HTML, no string-built SQL

## Data Integrity

- Is the migration backwards-compatible? (can old code run against the new schema during deploy?)
- Is data loss possible? (column drops, type narrowing, cascade deletes)
- Is there a rollback path for this migration?
- Are default values sensible for existing rows?

## Operational Readiness

- Works in production, not just locally? (env vars, paths, permissions, TLS)
- Structured logs at key decision points with correlation IDs?
- Timeouts and retries configured? (no unbounded waits; backoff on retries)
- What happens when a dependency fails? (graceful degradation vs. crash)
- Blast radius? (one user, one tenant, all users?)
- Deployment concern? (feature flag, config change, ordering dependency?)
- Rollback plan? (revert, flag off, migration rollback, or "hope"?)
- Safe to deploy on a Friday? If not, why?

## Output Format

```
## Summary
[1-2 sentence overview: what the change does and your overall read]

## Auto-Fixed
- [mechanical fixes already applied, with file:line]

## Findings
### [SEVERITY] Finding title
**Category**: Correctness | Security | Data Integrity | Ops | Performance
**Location**: file:line
**Recommendation**: [specific action]
**Why**: [brief rationale]
```

Severity: **Critical** (must fix before merge), **Warning** (should fix), **Note** (consider).

If there are no findings, say so plainly — don't manufacture issues to look thorough.

## Composition

On Claude Code, the `ccr` alias drives a multi-agent flow (`/review-pr` locally, `/code-review` plugin for PRs with GitHub comments). This skill is the single-reviewer rubric those agents and any other vendor (Codex, Cursor, Pi) share — invoke it directly when you want one focused pass, or let it back the multi-agent orchestration.
