#!/usr/bin/env bash
# Idempotently add repository-instruction block to ~/.claude/CLAUDE.md (system-wide).
# Safe to run from install.sh or one-off: dotfiles claude-instructions

# https://code.claude.com/docs/en/memory

set -e

CLAUDE_MD="${CLAUDE_MD:-$HOME/.claude/CLAUDE.md}"
# Unique block so we only add once
MARKER="AGENTS.md in this repository if present"
INSTRUCTION="Read and follow the instructions in AGENTS.md in this repository if present. Look for ABSTRACT.md for context on this repository."

ensure_claude_instructions() {
    mkdir -p "$(dirname "$CLAUDE_MD")"
    if [[ -f "$CLAUDE_MD" ]] && grep -q "$MARKER" "$CLAUDE_MD" 2>/dev/null; then
        return 0
    fi
    if [[ -f "$CLAUDE_MD" ]]; then
        [[ -s "$CLAUDE_MD" ]] && echo "" >> "$CLAUDE_MD"
        echo "$INSTRUCTION" >> "$CLAUDE_MD"
    else
        echo "$INSTRUCTION" >> "$CLAUDE_MD"
    fi
}

ensure_claude_instructions
