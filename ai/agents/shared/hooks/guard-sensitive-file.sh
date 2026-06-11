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

# Match on the basename so a bare `.env` (no leading dir) is caught — the old
# */.env globs required a slash and silently allowed `.env` and `.env.local`,
# the most common secret files. Templates (.env.example) and *.pub public keys
# are explicitly allowed. Vector contract: cli .../test_guard_hooks.py.
base=${FILE##*/}
deny=""
case "$base" in
    .env.example | .env.sample | .env.template | .env.dist | *.pub) ;; # safe templates / public keys
    .env | .env.* | *.env | *credentials* | *secrets.json | *secrets.yaml | *secrets.yml) deny=1 ;;
    id_rsa | id_dsa | id_ecdsa | id_ed25519 | id_rsa.* | id_dsa.* | id_ecdsa.* | id_ed25519.*) deny=1 ;;
    *.pem | *.p12 | *.pfx | *.key | *.keystore | *.jks | .netrc | .pgpass | .npmrc | .pypirc) deny=1 ;;
esac

if [[ -n "$deny" ]]; then
    printf 'BLOCK: %s is a sensitive file — edit it manually.\n' "$FILE" >&2
    printf 'Blocked by ai/agents/shared/hooks/guard-sensitive-file.sh.\n' >&2
    exit 2
fi

exit 0
