#!/usr/bin/env bash
# Deploy Cursor agentic config: MCP servers, rules, cli-config, plugin registration.
# Idempotent — safe to run multiple times.
#
# Usage:
#   ./setup.sh                 # Additive merge for shared MCPs (preserve local machine differences)
#   ./setup.sh --reset-mcp     # Reset managed MCP entries to dotfiles defaults

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
MCP_SKIP_FILE="$HOME/.config/dotfiles/mcp-skip"
PROFILE_FILE="$HOME/.config/dotfiles/profile"
RESET_MCP=false

# Parse --work / --personal flag (may be passed from parent dotfiles CLI)
DOTFILES_PROFILE="${DOTFILES_PROFILE:-}"
for arg in "$@"; do
    case "$arg" in
        --work) DOTFILES_PROFILE="work" ;;
        --personal) DOTFILES_PROFILE="personal" ;;
        --reset-mcp) RESET_MCP=true ;;
    esac
done

# Fall back to persistent profile file, then default to "personal"
if [[ -z "$DOTFILES_PROFILE" ]] && [[ -f "$PROFILE_FILE" ]]; then
    DOTFILES_PROFILE=$(head -1 "$PROFILE_FILE" | tr -d '[:space:]')
fi
DOTFILES_PROFILE="${DOTFILES_PROFILE:-personal}"

# Load persistent MCP skip list (one server per line), merge with MCP_SKIP env var
if [[ -f "$MCP_SKIP_FILE" ]]; then
    file_skips=$(grep -v '^#' "$MCP_SKIP_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
    MCP_SKIP="${MCP_SKIP:+$MCP_SKIP,}$file_skips"
fi

# Source print utils
source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null || true

require_jq() {
    command -v jq >/dev/null 2>&1 || { print_warning "jq not found — skipping"; return 1; }
}

# --- Merge shared MCP servers into editors/cursor/mcp.json ---
# Default: additive merge (preserve custom/machine-specific differences).
# Optional: --reset-mcp removes managed shared keys first, then re-adds current profile.
setup_mcp() {
    [[ -f "$SHARED_DIR/mcp-servers.json" ]] || return 0
    require_jq || return 0

    local mcp_file="$DOTFILES_DIR/editors/cursor/mcp.json"
    mkdir -p "$(dirname "$mcp_file")"

    # Read existing config (preserve custom servers)
    local existing='{}'
    if [[ -s "$mcp_file" ]]; then
        existing=$(jq '.' "$mcp_file" 2>/dev/null || echo '{}')
    fi

    # Build shared servers targeting cursor, strip targets field, skip MCP_SKIP entries
    local skip_json
    skip_json=$(if [[ -n "${MCP_SKIP:-}" ]]; then printf '%s' "$MCP_SKIP" | jq -Rc 'split(",")'; else echo '[]'; fi)

    local managed_keys
    managed_keys=$(jq '[
        to_entries
        | map(select(.value.targets | index("cursor")))
        | .[].key
    ]' "$SHARED_DIR/mcp-servers.json")

    local shared_servers
    shared_servers=$(jq --argjson skip "$skip_json" --arg profile "$DOTFILES_PROFILE" '{mcpServers: (
        to_entries
        | map(select(.value.targets | index("cursor")))
        | map(select(.value.profiles | index($profile)))
        | map(select(.key as $k | $skip | index($k) | not))
        | map({key: .key, value: (.value | del(.targets, .profiles))})
        | from_entries
    )}' "$SHARED_DIR/mcp-servers.json")

    if [[ "$RESET_MCP" == "true" ]]; then
        jq --argjson managed "$managed_keys" --argjson shared "$shared_servers" '
            .mcpServers = (
                ((.mcpServers // {}) | with_entries(select(.key as $k | ($managed | index($k) | not))))
                + $shared.mcpServers
            )
        ' <<< "$existing" > "$mcp_file"
        print_info "MCP reset mode enabled (--reset-mcp): managed shared entries refreshed"
    else
        jq --argjson shared "$shared_servers" '
            .mcpServers = ((.mcpServers // {}) + $shared.mcpServers)
        ' <<< "$existing" > "$mcp_file"
    fi

    local total shared_count
    total=$(jq '.mcpServers | length' "$mcp_file")
    shared_count=$(echo "$shared_servers" | jq '.mcpServers | length')
    print_success "MCP servers: $shared_count shared + $(( total - shared_count )) custom = $total total"
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

print_manual_steps() {
    print_info "Manual Cursor Marketplace steps (not automatable from setup scripts):"
    print_step "Install core plugins in Cursor chat:"
    print_step "/add-plugin superpowers"
    print_step "/add-plugin context7-plugin"
    print_step "/add-plugin neon-postgres"
    print_step "/add-plugin svelte"
    print_step "After Neon install, run: Get started with Neon (completes authentication)"
    print_step "See $SCRIPT_DIR/PLUGINS.md for personal/work plugin sets"
}

# --- Main ---
setup_mcp
setup_rules
setup_universal_rules
setup_cli_config
setup_plugin
setup_cursorignore
print_manual_steps
