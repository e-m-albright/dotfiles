#!/usr/bin/env bash
# Block edits/writes to sensitive files (credentials, private keys, env secrets).
# Vendor-agnostic: reads the target path from whichever JSON key the harness uses
# (Claude/Codex: .tool_input.file_path · Cursor: .filePath / .file_path).
# Exit 2 with a stderr message to BLOCK; exit 0 to allow.
#
# Deployed verbatim to every hook-capable vendor so the safety contract is uniform.

set -eo pipefail

INPUT=$(cat 2>/dev/null || true)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .filePath // .file_path // empty' 2>/dev/null || true)
[[ -z "$FILE" ]] && exit 0

case "$FILE" in
    */credentials*|*id_rsa*|*id_ed25519*|*id_ecdsa*|*.pem|*.p12|*.pfx|*/.env|*/.env.*)
        printf 'BLOCK: %s is a sensitive file — edit it manually.\n' "$FILE" >&2
        printf 'Blocked by ai/agents/shared/hooks/guard-sensitive-file.sh.\n' >&2
        exit 2
        ;;
esac

exit 0
