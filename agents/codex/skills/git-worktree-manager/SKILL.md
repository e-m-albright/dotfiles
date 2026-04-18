---
name: git-worktree-manager
description: Create, list, and clean up git worktrees with smart naming and branch conventions
disable-model-invocation: true
---

# Git Worktree Manager

Manage git worktrees for isolated feature work.

## Commands

### Create a new worktree

```bash
# Pick a descriptive name — the skill creates the worktree + branch
WORKTREE_NAME="$1"  # e.g., "auth-refactor"
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREE_DIR="$REPO_ROOT/.claude/worktrees/$WORKTREE_NAME"

git worktree add -b "worktree-$WORKTREE_NAME" "$WORKTREE_DIR" main
```

### List active worktrees

```bash
git worktree list
```

Show each worktree's branch, last commit date, and whether it has uncommitted changes.

### Clean up stale worktrees

```bash
# Find worktrees with no uncommitted changes whose branches are merged to main
git worktree list --porcelain | grep '^worktree ' | sed 's/worktree //' | while read -r wt; do
    [[ "$wt" == "$(git rev-parse --show-toplevel)" ]] && continue
    if git -C "$wt" diff --quiet && git -C "$wt" diff --cached --quiet; then
        echo "Clean: $wt"
    else
        echo "Dirty: $wt (has uncommitted changes)"
    fi
done
```

Prompt before removing. Never force-remove worktrees with uncommitted changes.

### Prune dead references

```bash
git worktree prune
```

## Workflow

1. Ask what the user wants: create, list, or clean
2. For create: ask for a name, create worktree under `.claude/worktrees/`
3. For list: show all worktrees with status
4. For clean: identify stale worktrees, confirm before removing
5. After cleanup, prune dead references and delete merged branches
