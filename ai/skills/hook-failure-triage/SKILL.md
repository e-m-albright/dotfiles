---
name: hook-failure-triage
description: Triage a failing pre-commit/pre-push hook (lefthook, husky, pre-commit) before retrying — preflight all gates upfront, name the failing recipe before fixing, and verify HEAD's tree after an amend or rebase. Use when a `git commit` or `git push` fails inside a hook, when the user says "the pre-commit hook failed", "my push is being rejected", "lefthook/husky failed", "why won't this commit", or before pushing a commit that was amended or rebased through hook rejections.
---

# Hook Failure Triage

When a `git commit` or `git push` fails inside a hook (lefthook, husky, pre-commit, etc.), the most expensive mistake is retrying blindly. The median recovery cost of a hook failure runs ~20-30 tool calls; most of that is spent re-running the wrong thing because the agent misread which sibling check failed.

## Preflight first, triage second

**Before committing on a fix branch, run the project's "all the gates the push hook runs" command in one shot** (e.g. `just verify`, `just ci preflight-fast`, `npm run lint && npm test`, whatever the project exposes). Discover gates iteratively — commit → push → em-dash fail → fix → push → lint fail → fix → push — and you burn N round trips for what one preflight catches in one. The gates are independent, so the next one always might also fail.

**Find recipes via the task runner's own index, not by grepping implementation files.** `just`, `just --list`, `npm run`, `make help`, etc. list every top-level recipe. Grepping `lefthook.yml` / `.husky/` for hook scripts only finds the constituent steps; umbrella recipes (preflight, verify, all-blocking) live alongside them but never appear in the hook config.

## The rule (when a hook does fail)

Before re-staging, re-running, or "fixing" anything in response to a hook failure:

1. **Find the exact failing recipe name** in the hook output. Hooks list each check by name; the block usually ends with `Recipe <name> failed with exit code <N>` or similar.
2. **Read the captured stdout/stderr for that recipe only.** Parallel hook runners interleave output; confirm you are reading the failing recipe's lines, not its neighbour's. Set the verbose env var (`LEFTHOOK_VERBOSE=1`, `DEBUG=1`, etc.) for one full-output run if you need it.
3. **State the failing recipe + the specific check that tripped** before proposing a fix. ("`web-lint` failed: biome reported 3 unused imports in `src/foo.ts`.")

If the failure block doesn't explain itself, run the recipe in isolation rather than retrying the whole hook. The hook orchestrator is just a wrapper.

## After amend or rebase: verify HEAD's tree before pushing

`git commit --amend` and `git rebase` are easy to get wrong when fighting through hook rejections. Two failure modes that bite repeatedly:

1. **Autostash + restore strips fixes.** `git rebase` autostashes uncommitted changes; a later `git restore --staged --worktree .` (intended to clean up "autostash garbage") silently strips fixes that were in the working tree but not yet in the commit. The push then ships a commit that does NOT contain the fixes you just verified locally.

2. **Amend rewrites the wrong commit.** If a previous commit attempt left files staged (e.g., commit-msg hook rejected the subject), the next `git commit --amend` folds the staged changes into the PREVIOUS HEAD commit — not creating a new commit on top. If the previous commit was already pushed, your local history diverges and a force push would be needed.

Before pushing any commit you've amended or rebased through:

```bash
git log --oneline -3                                          # confirm shape matches your mental model
git diff-tree --no-commit-id --name-status -r HEAD            # files actually in HEAD
git show HEAD:path/to/file | grep <expected-content>          # spot-check load-bearing edits
git rev-parse HEAD origin/<branch>                            # confirm fast-forward, not divergent
```

If `origin/<branch>` is not an ancestor of HEAD and you didn't intend to rewrite history, **stop**: reset back to the published commit and rebuild your changes on top of it. Force-push to a shared branch is never the right next step without explicit user authorization.

## Anti-patterns

- Re-staging and re-committing without identifying the recipe.
- "Fixing" a file owned by a parallel agent because its lint warning was the loudest line in the output (see `multi-agent.mdc`).
- Bypassing with `--no-verify`. The hooks are intentional; the work is reading them correctly.
- Discovering gates one at a time after each push failure instead of running preflight once upfront.
- Trusting `git commit --amend` output without `git show HEAD:path | grep ...` verifying the tree.
- **Reaching for the cache eraser.** If your recovery is `rm -rf .pytest_cache`, `node_modules`, `.next`, `target`, or any "delete state and try again," stop. Repeated cache deletion means the tool isn't a fit, not that you got unlucky. Either find the documented correct usage (config, version, flag combo) and apply it permanently, or replace the tool. Cache-eraser recovery hides root causes, breaks across machines, and erodes trust in the toolchain.

## Cross-references

- `multi-agent.mdc` — etiquette when failures span agent-owned files
- Project-specific hook config (`lefthook.yml`, `.husky/`, `.pre-commit-config.yaml`) — the recipe names live there

_Promoted from `.ai/rules/process/hook-failure-triage.mdc` (was an always-on rule; now an on-demand skill)._
