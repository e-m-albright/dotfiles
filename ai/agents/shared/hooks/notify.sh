#!/usr/bin/env bash
# Desktop notification when an agent finishes a turn or needs input.
# Vendor-agnostic: derives the label from the environment so every vendor wires
# the same script. Override message/sound via NOTIFY_MESSAGE / NOTIFY_SOUND.
# Always exits 0 — notification is cosmetic and must never block the agent.

set -eo pipefail

if [ -n "${CURSOR_AGENT:-}" ]; then
    LABEL="Cursor"
    DIR=$(basename "$PWD")
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    LABEL="Claude Code"
    DIR=$(basename "$CLAUDE_PROJECT_DIR")
else
    LABEL="Codex"
    DIR=$(basename "$PWD")
fi

MSG="${NOTIFY_MESSAGE:-Done — ready for input}"
SOUND="${NOTIFY_SOUND:-Glass}"

printf '\a' > /dev/tty 2>/dev/null || true
terminal-notifier -title "$LABEL · $DIR" -message "$MSG" -sound "$SOUND" 2>/dev/null || true
exit 0
