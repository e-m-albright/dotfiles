#!/usr/bin/env bash
# Auto-format files after Claude Code edits them.
# Called as a PostToolUse hook on Edit/Write operations.
# Reads tool input JSON from stdin to get the file path.

set -eo pipefail

FILE=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
    *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc)
        # Biome if configured, otherwise skip
        if [[ -f "biome.json" || -f "biome.jsonc" ]]; then
            npx biome check --fix --unsafe "$FILE" 2>/dev/null || true
        elif command -v prettier >/dev/null 2>&1; then
            npx prettier --write "$FILE" 2>/dev/null || true
        fi
        ;;
    *.svelte)
        if [[ -f "biome.json" || -f "biome.jsonc" ]]; then
            npx biome check --fix --unsafe "$FILE" 2>/dev/null || true
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
esac
