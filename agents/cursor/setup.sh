#!/usr/bin/env bash
# Deploy Cursor agentic config: MCP servers, rules, cli-config, plugin registration.
# Idempotent — safe to run multiple times.
#
# Usage:
#   ./setup.sh                 # Additive merge for shared MCPs (preserve custom)
#   ./setup.sh --reset-mcp     # Reset managed MCP entries to dotfiles defaults

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"

source "$SHARED_DIR/lib.sh"
agentlib_init "$@"

# --- Merge shared MCP servers into editors/cursor/mcp.json ---
setup_mcp() {
    [[ -f "$SHARED_MCP_JSON" ]] || return 0
    require_jq || return 0

    local mcp_file="$DOTFILES_DIR/editors/cursor/mcp.json"
    mkdir -p "$(dirname "$mcp_file")"

    local existing='{}'
    [[ -s "$mcp_file" ]] && existing=$(jq '.' "$mcp_file" 2>/dev/null || echo '{}')

    local managed_keys shared_servers
    managed_keys=$(mcp_managed_keys cursor)
    shared_servers=$(mcp_servers_for cursor)

    if [[ "$RESET_MCP" == "true" ]]; then
        jq --argjson managed "$managed_keys" --argjson shared "$shared_servers" '
            .mcpServers = (
                ((.mcpServers // {}) | with_entries(select(.key as $k | ($managed | index($k) | not))))
                + $shared
            )
        ' <<< "$existing" > "$mcp_file"
        print_info "MCP reset mode enabled (--reset-mcp): managed shared entries refreshed"
    else
        jq --argjson shared "$shared_servers" '.mcpServers = ((.mcpServers // {}) + $shared)' \
            <<< "$existing" > "$mcp_file"
    fi

    local total shared_count
    total=$(jq '.mcpServers | length' "$mcp_file")
    shared_count=$(echo "$shared_servers" | jq 'length')
    print_success "MCP servers: $shared_count shared + $(( total - shared_count )) custom = $total total"
}

# --- Generate shared-rules.mdc (Cursor-formatted with frontmatter) ---
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
    [[ -f "$SCRIPT_DIR/cli-config.json" ]] || return 0
    ln -sf "$SCRIPT_DIR/cli-config.json" ~/.cursor/cli-config.json
    print_success "Deployed cli-config.json"
}

# --- Register dotfiles as a local Cursor plugin ---
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

print_manual_steps() {
    print_info "Manual Cursor Marketplace steps (not automatable from setup scripts):"
    print_step "Install core plugins in Cursor chat:"
    print_step "/add-plugin superpowers"
    print_step "/add-plugin context7-plugin"
    print_step "See $SCRIPT_DIR/PLUGINS.md for personal/work plugin sets"
}

setup_mcp
setup_rules
symlink_process_rules "$SCRIPT_DIR/rules" .mdc
setup_cli_config
setup_plugin
setup_cursorignore
print_manual_steps
