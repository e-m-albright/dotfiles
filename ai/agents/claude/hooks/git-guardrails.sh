#!/usr/bin/env bash
# Block destructive git operations and hook bypasses.
# Reads JSON tool input from stdin (Claude Code PreToolUse hook protocol).
# Exits 2 with a stderr message to block; exits 0 to allow.
#
# Policy aligns with ~/dotfiles/CLAUDE.md:
#   - Never run destructive git operations unless explicitly authorized.
#   - Never skip hooks (--no-verify) or bypass signing.

set -eo pipefail

CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null || echo "")
[[ -z "$CMD" ]] && exit 0

block() {
    local reason="$1"
    {
        printf 'BLOCK: %s\n' "$reason"
        printf 'Command: %s\n' "$CMD"
        printf '\nThis is blocked by ~/dotfiles/ai/agents/claude/hooks/git-guardrails.sh.\n'
        printf 'If genuinely needed, the user must authorize this specific command explicitly.\n'
        printf 'Reference: ~/dotfiles/CLAUDE.md "Never run destructive git operations".\n'
    } >&2
    exit 2
}

# Force push (any --force form, including alone or with target)
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]]+push[[:space:]]+([^&;|]*[[:space:]])?(--force([^-]|$)|-f[[:space:]])'; then
    block 'force push detected. Use --force-with-lease only with explicit user authorization.'
fi

# Hard reset (loses uncommitted work irrecoverably)
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]]+reset[[:space:]]+(--hard|-{1,2}h)([[:space:]]|$)'; then
    block 'git reset --hard discards uncommitted work.'
fi

# Clean -f (deletes untracked files)
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f'; then
    block 'git clean -f deletes untracked files. Use git status / git stash first.'
fi

# Branch force-deletion
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]]+branch[[:space:]]+(-D|--delete[[:space:]]+--force)'; then
    block 'git branch -D destructively deletes branches without merge check.'
fi

# Hook bypass (--no-verify on any git command)
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]].*--no-verify'; then
    block '--no-verify bypasses pre-commit/pre-push hooks. Investigate the hook failure instead.'
fi

# Signing bypass
if echo "$CMD" | grep -qE '(^|[[:space:]])git[[:space:]].*(--no-gpg-sign|-c[[:space:]]+commit\.gpgsign=false)'; then
    block 'GPG signing bypass detected. Sign commits unless the user has explicitly opted out for this command.'
fi

exit 0
