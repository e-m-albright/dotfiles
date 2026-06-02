#!/usr/bin/env bash
# Shim: normalize Cursor afterFileEdit input to Claude Code PostToolUse format.
# Cursor may provide file path under different JSON keys.
# This shim tries multiple keys and forwards to the shared formatter.

set -eo pipefail

INPUT=$(cat)

# Try Cursor's likely key names, fall back to Claude Code's format
FILE=$(echo "$INPUT" | jq -r '.filePath // .file_path // .tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

# Forward in Claude Code's expected format
echo "{\"tool_input\": {\"file_path\": \"$FILE\"}}" | \
    "$(dirname "$0")/../../claude/hooks/format-on-save.sh"
