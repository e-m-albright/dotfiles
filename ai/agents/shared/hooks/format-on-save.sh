#!/usr/bin/env bash
# Auto-format a file after an agent edits it (post-edit hook).
# Vendor-agnostic: reads the path from whichever JSON key the harness uses
# (Claude/Codex: .tool_input.file_path · Cursor afterFileEdit: .filePath / .file_path).
# Always exits 0 — formatting is best-effort and must never block the agent.
#
# Deployed verbatim to every hook-capable vendor so formatting is uniform.

set -eo pipefail

INPUT=$(cat 2>/dev/null || true)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .filePath // .file_path // empty' 2>/dev/null || true)
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
    *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc)
        if [[ -f "biome.json" || -f "biome.jsonc" ]]; then
            npx biome check --fix "$FILE" 2>/dev/null || true
        elif command -v prettier >/dev/null 2>&1; then
            npx prettier --write "$FILE" 2>/dev/null || true
        fi
        ;;
    *.svelte)
        if [[ -f "biome.json" || -f "biome.jsonc" ]]; then
            npx biome check --fix "$FILE" 2>/dev/null || true
        fi
        ;;
    *.py)
        if command -v ruff >/dev/null 2>&1; then
            ruff check --fix --quiet "$FILE" 2>/dev/null || true
            ruff format --quiet "$FILE" 2>/dev/null || true
        fi
        ;;
    *.rs)
        if command -v rustfmt >/dev/null 2>&1; then
            rustfmt --edition 2021 "$FILE" 2>/dev/null || true
        fi
        ;;
    *.go)
        if command -v gofmt >/dev/null 2>&1; then
            gofmt -w "$FILE" 2>/dev/null || true
        fi
        if command -v goimports >/dev/null 2>&1; then
            goimports -w "$FILE" 2>/dev/null || true
        fi
        ;;
    *.sh)
        if command -v shellcheck >/dev/null 2>&1; then
            shellcheck -S warning "$FILE" 2>/dev/null || true
        fi
        ;;
esac
