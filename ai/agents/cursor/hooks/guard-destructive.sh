#!/usr/bin/env bash
# Guard against destructive shell commands in Cursor agent.
# Exit 2 to block the command.

set -eo pipefail

CMD=$(jq -r '.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0

case "$CMD" in
    *"rm -rf /"*|*"rm -rf ~"*|*"rm -rf \$HOME"*)
        echo "BLOCK: Destructive rm command" >&2
        exit 2 ;;
    *"git reset --hard"*|*"git clean -fd"*|*"git checkout -- ."*)
        echo "BLOCK: Destructive git command — confirm manually" >&2
        exit 2 ;;
    *"sudo rm"*|*"sudo dd"*)
        echo "BLOCK: Privileged destructive command" >&2
        exit 2 ;;
esac
