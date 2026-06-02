---
name: pr-summary
description: Generate a pull request description from diff and commit history, then create the PR via `gh`. Use when user says "open a PR", "create a pull request", "push and PR this", "draft a PR description", "summarise this branch", or wants a structured PR body for an existing branch.
---

# PR Summary

Generate a well-structured pull request from the current branch's changes.

## Workflow

1. Gather context:

```bash
# What branch are we on, what's the base?
git branch --show-current
git log --oneline main..HEAD

# Full diff for analysis
git diff main...HEAD --stat
git diff main...HEAD
```

2. Analyze the changes:
   - Group commits by type (feat/fix/refactor/docs/test)
   - Identify the main purpose of the PR
   - Note any breaking changes
   - List files changed with brief descriptions

3. Generate PR title and body:
   - Title: short (<70 chars), imperative mood, matches primary commit type
   - Body format:

```markdown
## Summary
- [1-3 bullet points describing what and why]

## Changes
- [Grouped by area/type, with file references]

## Test plan
- [ ] [How to verify each change]

## Breaking changes
[If any — migration steps]
```

4. Create the PR:

```bash
gh pr create --title "title" --body "body"
```

5. Report the PR URL

## Notes

- If the branch has a single commit, use its message as the title
- If commits reference Linear issues (e.g., ENG-123), include them in the body
- Always include a test plan, even if it's just "run existing tests"
- Ask the user to review the draft before creating if the PR is large (>10 files)
- For conventions on writing good titles, summaries, test plans, and commits, see [Writing tickets & PRs](references/writing-tickets-prs.md)
