#!/usr/bin/env bash
# Deploy Cursor agentic config: MCP servers, rules, cli-config, plugin registration.
# Idempotent — safe to run multiple times.

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"

# Source print utils
source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null || true

require_jq() {
    command -v jq >/dev/null 2>&1 || { print_warning "jq not found — skipping"; return 1; }
}

# --- Generate .mcp.json from shared source ---
setup_mcp() {
    [[ -f "$SHARED_DIR/mcp-servers.json" ]] || return 0
    require_jq || return 0

    jq '{mcpServers: (
        to_entries
        | map(select(.value.targets | index("cursor")))
        | map({key: .key, value: (.value | del(.targets))})
        | from_entries
    )}' "$SHARED_DIR/mcp-servers.json" > "$SCRIPT_DIR/.mcp.json"

    local count
    count=$(jq '.mcpServers | length' "$SCRIPT_DIR/.mcp.json")
    print_success "Generated .mcp.json ($count servers)"
}

# --- Generate rules from shared source ---
setup_rules() {
    [[ -f "$SHARED_DIR/rules.md" ]] || return 0
    mkdir -p "$SCRIPT_DIR/rules"

    cat > "$SCRIPT_DIR/rules/shared-rules.mdc" << RULES_EOF
---
description: Shared agentic guardrails — process, safety, context, testing
alwaysApply: true
---

$(cat "$SHARED_DIR/rules.md")
RULES_EOF

    print_success "Generated rules/shared-rules.mdc"
}

# --- Deploy cli-config.json ---
setup_cli_config() {
    mkdir -p ~/.cursor
    if [[ -f "$SCRIPT_DIR/cli-config.json" ]]; then
        ln -sf "$SCRIPT_DIR/cli-config.json" ~/.cursor/cli-config.json
        print_success "Deployed cli-config.json"
    fi
}

# --- Register as local plugin ---
setup_plugin() {
    mkdir -p ~/.cursor/plugins
    if [[ -L ~/.cursor/plugins/dotfiles ]] && [[ "$(readlink ~/.cursor/plugins/dotfiles)" == "$SCRIPT_DIR" ]]; then
        print_skip "Plugin already registered"
    else
        ln -sf "$SCRIPT_DIR" ~/.cursor/plugins/dotfiles
        print_success "Registered dotfiles plugin (~/.cursor/plugins/dotfiles)"
    fi
    print_info "Ensure third-party plugins are enabled: Cursor Settings > Features"
}

# --- Generate .cursorignore from shared patterns ---
setup_cursorignore() {
    [[ -f "$SHARED_DIR/ignore-patterns" ]] || return 0
    local cursor_ignore="$DOTFILES_DIR/editors/cursor/.cursorignore"

    cat > "$cursor_ignore" << 'HEADER'
# Cursor ignore file
# AUTO-GENERATED from agents/shared/ignore-patterns + Cursor-specific additions
# Do not edit directly — modify agents/shared/ignore-patterns instead

HEADER

    cat "$SHARED_DIR/ignore-patterns" >> "$cursor_ignore"

    cat >> "$cursor_ignore" << 'CURSOR_SPECIFIC'

# Cursor-specific
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db
.cache/
CURSOR_SPECIFIC

    print_success "Generated .cursorignore"
}

# --- Universal rules (symlinked to dotfiles) ---
setup_universal_rules() {
    local rules_source="$DOTFILES_DIR/.ai/rules/process"
    local rules_dest="$SCRIPT_DIR/rules"

    [[ -d "$rules_source" ]] || return 0

    mkdir -p "$rules_dest"

    for rule in "$rules_source"/*.mdc; do
        [[ -f "$rule" ]] || continue
        local rule_name
        rule_name="$(basename "$rule")"
        local dest="$rules_dest/$rule_name"

        if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$rule" ]]; then
            continue
        fi

        ln -sf "$rule" "$dest"
    done

    local total
    total=$(find "$rules_source" -name '*.mdc' -type f | wc -l | tr -d ' ')
    print_success "Symlinked $total universal rules (cursor/rules/ → dotfiles)"
}

# --- Main ---
setup_mcp
setup_rules
setup_universal_rules
setup_cli_config
setup_plugin
setup_cursorignore
