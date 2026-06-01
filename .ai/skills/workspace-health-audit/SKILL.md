---
name: workspace-health-audit
description: Audit workspace integration health — orphaned stashes, stale branches/worktrees, open/stale PRs, duplicate definitions from parallel agents, pattern divergence from bad merges, and misplaced agentic artifacts. Use when multiple agents have been working in parallel, after a merge wave, or as a periodic hygiene check. Complements `git-worktree-manager` (narrow worktree CRUD) with broader cross-tool hygiene.
---

# Workspace Health Audit

Detect integration failures that arise when multiple agents (or humans) work in parallel: orphaned artifacts, stale state, duplicate definitions, and pattern divergence from merge conflicts resolved mechanically rather than thoughtfully.

## When to Use

- After a wave of parallel agent work lands on main
- When the user suspects agents reverted or stomped each other's changes
- Periodic hygiene check (weekly or before a milestone)
- Before starting a new phase of work to confirm a clean baseline

## Audit Checklist

Run each section that applies to the repo. Report findings in a summary table at the end with severity (HIGH / MEDIUM / LOW / CLEAN) per section.

### 1. Stash Triage

```bash
git stash list
```

For each entry:
1. `git stash show stash@{N} --stat` — identify touched files.
2. Check if the work already landed on main (`git log --oneline --grep=...`).
3. If the stash base branch still exists, diff against HEAD to measure staleness.
4. **Verdict:** DROP (superseded), RECOVER (lost work), or ASK (ambiguous).

Goal: empty stash.

### 2. Worktree Inventory

```bash
git worktree list
ls -la .claude/worktrees/ .worktrees/ 2>/dev/null   # common per-project conventions
```

For each non-main worktree:
1. Check if its HEAD is reachable from main (`git merge-base --is-ancestor`).
2. Check for uncommitted changes (`git -C <path> status --short`).
3. If merged and clean: candidate for removal.
4. If it has unmerged work: flag for review.

Goal: single integration worktree + only-active feature worktrees.

### 3. Branch Hygiene

```bash
git branch -a --sort=-committerdate
git remote prune origin --dry-run
```

**Permanent branches:** read the repo's CONTRIBUTING / AGENTS / README to identify them. Common patterns:
- `main` — production trunk
- `dev` / `develop` — integration branch
- `scanners`, `gh-pages`, `staging` — long-lived automation/deploy branches

Any other branch is a candidate for cleanup.

Categorize every non-permanent branch:
- **Merged:** `git log --oneline main..origin/<branch>` is empty → safe to delete.
- **Superseded:** work landed via different commits → delete with note.
- **Unmerged with value:** unique content not on main → flag for cherry-pick or merge.
- **Stale:** last commit > 14 days old and unmerged → flag for review or deletion.
- **Workflow output:** auto-generated branches from CI cron jobs (see §3a).

#### 3a. Workflow-generated branch recognition

Automated workflows often push branches without opening PRs. Recognize and bulk-prune them. Common prefixes:

| Prefix / pattern | Likely source | Default disposition |
|------------------|---------------|---------------------|
| `worktree-*`, `worktree-agent-*` | Local agent worktree leftovers pushed by mistake | Delete; worktree dirs should be gitignored |
| `auto-ratchet/*` | Automated code-health threshold bumps | Delete once threshold raised in config |
| `audit/<topic>-YYYY-MM-DD-*` | Automated audit runs committing findings | Delete once findings actioned |
| `dependabot/*`, `renovate/*` | Dep bots | Leave for the bot's normal lifecycle |

**Bulk-delete pattern (after confirming no open PRs reference them):**
```bash
gh pr list --state open --json headRefName --jq '.[].headRefName' > /tmp/pr-heads.txt
git branch -r | grep -E 'origin/(worktree-|auto-ratchet/|audit/)' \
  | sed 's|  origin/||' | grep -vFf /tmp/pr-heads.txt \
  | xargs -n1 -I{} git push origin --delete {}
```

Report bulk deletions as a single summary line, not one entry per branch.

Severity: HIGH if workflow branches outnumber human branches by 3:1 or more — something automated is misconfigured.

### 4. Pull Request Triage

Collect all open PRs and categorize them. This surfaces forgotten work, stale reviews, and PRs that should have been closed after a direct merge.

```bash
gh pr list --state open --json number,title,headRefName,baseRefName,state,isDraft,createdAt,updatedAt,mergeable,reviewDecision,statusCheckRollup,author

# Also check recently closed for accidental closures
gh pr list --state closed --json number,title,headRefName,closedAt,mergedAt --limit 20
```

For each open PR, categorize:

- **Ready to merge:** All checks pass, approved (or no review required), not draft. → merge or flag for immediate merge.
- **Stale:** Updated > 7 days ago with no activity. Compare `gh pr diff` against current main — if the work already landed via direct merge, close with comment. Otherwise flag.
- **Superseded:** Branch already merged to main directly (common with worktree workflows). Close with "landed via direct merge" comment.
- **Draft / WIP:** Note as in-progress.
- **Blocked:** Failing checks or requested changes. Diagnose the blocker.
- **Orphaned:** PR branch deleted or force-pushed away. Close.

Goal: zero open PRs that should be closed; zero closed PRs with lost work.

### 5. Duplicate Definitions (highest-value check)

Search for the same symbol defined in multiple locations. Focus on types parallel agents commonly duplicate:

**Python enums and models:**
```bash
grep -rn "class \w\+\(.*\(Enum\|BaseModel\)" . --include="*.py" | grep -v __pycache__
```
Group by class name. Flag any name appearing more than once — especially if the base types differ (StrEnum vs IntEnum, Pydantic v1 vs v2).

**Rust types:**
```bash
grep -rn "pub enum \|pub struct " . --include="*.rs"
```
Group by name. Flag duplicates that aren't in `tests/` or behind `#[cfg(test)]`.

**TypeScript types:**
```bash
grep -rnE "(export )?(interface|type) \w+" . --include="*.ts"
```

**Import consistency:**
For each duplicate found, trace all importers and verify they import from the canonical location.

### 6. Pattern Adoption Consistency

Check that patterns established by one workstream were adopted by all peers. Examples:

- **Factory pattern:** if a module establishes a `make_*` / `build_*` / `lazy_*` factory pattern, every peer should use it. Flag old `_build_*()` or one-off helpers.
- **Shared infrastructure:** check that shared modules are declared in their crate's `lib.rs` / package `index.ts` and have at least one importer. Flag orphaned modules.
- **Re-export / backward compat:** after a god-module split, check that parent modules re-export extracted symbols or that all callers updated their imports.

### 7. Compilation & Type Health

Run compilation checks as a final signal:

```bash
# Rust
cargo check 2>&1 | tail -20

# Python (if pyright/mypy configured)
pyright --outputjson 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(f'errors={d[\"summary\"][\"errorCount\"]} warnings={d[\"summary\"][\"warningCount\"]}')"

# TypeScript
tsc --noEmit
```

### 8. Dead Code Scan (lightweight)

Check for files that exist on disk but aren't imported or declared anywhere:

- **Rust:** For each `.rs` file in `src/`, verify it's either `mod`-declared in `lib.rs`/`main.rs` or is `lib.rs`/`main.rs`/`build.rs` itself.
- **Python:** For each `.py` file, verify it's either imported somewhere or is `__init__.py`/`conftest.py`/`__main__.py`.
- **Web (SvelteKit / Next.js):** Route files (`+page.svelte`, `page.tsx`, etc.) are discovered by the framework's filesystem router, **not** by imports. They will always appear as zero-importer files to static analysis tools. Never flag or delete route files based on import analysis. To verify a route is dead, check the running app — not the import graph.

### 9. Misplaced Artifacts

Scan tracked directories for files that look like working artifacts rather than permanent fixtures.

**Date-prefixed files in permanent directories:**
```bash
find docs/ .ai/ -name "????-??-??-*" -type f 2>/dev/null
```
Date-prefixed files (`YYYY-MM-DD-*`) are a strong signal of session-specific working artifacts. They belong in `.ai/artifacts/`, not tracked directories. Exception: files in `docs/specs/` or `docs/strategy/` may legitimately use date prefixes for versioned baselines.

**Bootstrap/handoff language in tracked files:**
```bash
grep -rl "continue from\|bootstrap\|handoff\|next session\|context transfer" docs/ --include="*.md" 2>/dev/null
```
Files containing session-continuation language are working artifacts.

**Stray markdown in project root:**
```bash
ls *.md 2>/dev/null | grep -v "README\|LICENSE\|CHANGELOG\|AGENTS\|CONTRIBUTING\|SECURITY"
```
Unexpected `.md` files in the root are often agent output that missed its target.

For each finding outside an explicitly-permitted directory: flag with severity MEDIUM, recommend moving to the appropriate ephemeral location.

### 10. Stale Artifacts

Scan ephemeral artifact directories for forgotten files:

```bash
find .ai/artifacts/ -name "*.md" -mtime +30 2>/dev/null
```

For each file:
1. Check if the content was incorporated elsewhere (search for key phrases in git log or current codebase).
2. **Verdict:** DELETE (incorporated or abandoned), KEEP (still active), or ASK (ambiguous).

Goal: `.ai/artifacts/` contains only active working files, not a graveyard. Severity: LOW (these are local-only files, no git impact).

### 11. Tracked-but-Should-Be-Gitignored

```bash
git ls-files .ai/artifacts/ 2>/dev/null
```

If any files appear under a directory the project considers ephemeral, something is wrong with `.gitignore` or a file was force-added. Severity: HIGH.

## Output Format

```
## Workspace Health Audit — {date}

| Section | Status | Details |
|---------|--------|---------|
| Stash | CLEAN / n items | ... |
| Worktrees | CLEAN / n orphaned | ... |
| Branches | CLEAN / n stale | ... |
| Pull requests | CLEAN / n actionable | ... |
| Duplicate defs | CLEAN / n conflicts | ... |
| Pattern adoption | CLEAN / n inconsistencies | ... |
| Compilation | CLEAN / n errors | ... |
| Dead code | CLEAN / n orphans | ... |
| Misplaced artifacts | CLEAN / n found | ... |
| Stale artifacts | CLEAN / n stale | ... |
| Tracked gitignored | CLEAN / n violations | ... |

### Findings

#### [Section]: [Finding title]
**Severity:** HIGH / MEDIUM / LOW
**Details:** ...
**Recommended action:** ...

### Actions Taken
(List any cleanup performed during the audit)

### Deferred for Next Wave
(List issues that need discussion or design decisions)
```

## Important Notes

- This skill is **read-mostly**. Only take destructive actions (dropping stashes, removing worktrees, deleting branches) when the user explicitly authorizes cleanup, not just audit.
- When in doubt about whether work is superseded, flag for review rather than deleting.
- The duplicate-definition check (§5) is the highest-value section — parallel agents creating conflicting types is the most dangerous failure mode because it compiles fine but produces runtime bugs.

## Cross-references

- `git-worktree-manager` skill — narrow CRUD on worktrees with smart naming
- `session-recovery` skill — when the audit reveals interrupted work to resume
