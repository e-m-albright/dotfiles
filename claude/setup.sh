#!/usr/bin/env bash
# Configure Claude Code: plugins, MCP servers, voice, and system instructions.
# Idempotent — safe to run multiple times.
#
# Usage:
#   ./setup.sh              # Full setup
#   dotfiles claude-setup   # Via dotfiles CLI alias
#
# What it does:
#   1. Ensures ~/.claude/CLAUDE.md has system instructions
#   2. Merges enabled plugins from plugins.yaml into settings.json
#   3. Enables voice mode
#   4. Configures MCP servers (if any defined)
#
# Plugin list lives in: ~/dotfiles/claude/plugins.yaml
# Permissions are managed separately by: ~/dotfiles/.agents/generate-permissions.sh

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
SETTINGS_FILE="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"
DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
PLUGINS_YAML="$SCRIPT_DIR/plugins.yaml"
MCP_JSON="$SCRIPT_DIR/mcp.json"
HOOKS_JSON="$SCRIPT_DIR/hooks.json"
GLOBAL_CLAUDE_MD="$SCRIPT_DIR/global-claude.md"
DESKTOP_PREFS="$SCRIPT_DIR/desktop-preferences.json"
MARKETPLACES_JSON="$SCRIPT_DIR/marketplaces.json"

# Source print utils if available
if [[ -n "${print_section:-}" ]] || source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null; then
    :
fi

# Require jq for all operations
require_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        print_warning "jq not found — skipping (brew install jq)"
        return 1
    fi
    return 0
}

# Helper: backup and ensure settings file exists
ensure_settings() {
    mkdir -p "$HOME/.claude"
    [[ -f "$SETTINGS_FILE" ]] || echo '{}' > "$SETTINGS_FILE"
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
}

# --- System instructions (CLAUDE.md) ---
setup_instructions() {
    [[ -f "$GLOBAL_CLAUDE_MD" ]] || { print_warning "No global-claude.md found"; return 0; }
    mkdir -p "$HOME/.claude"
    [[ -f "$HOME/.claude/CLAUDE.md" ]] && cp "$HOME/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md.bak"
    cp "$GLOBAL_CLAUDE_MD" "$HOME/.claude/CLAUDE.md"
    print_success "System instructions (~/.claude/CLAUDE.md)"
}

# --- Marketplaces ---
setup_marketplaces() {
    [[ -f "$MARKETPLACES_JSON" ]] || { print_info "No marketplaces.json found — skipping"; return 0; }
    require_jq || return 0

    ensure_settings

    local marketplaces
    marketplaces=$(jq '. // {}' "$MARKETPLACES_JSON")

    jq --argjson mkts "$marketplaces" '.extraKnownMarketplaces = ($mkts + (.extraKnownMarketplaces // {}))' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

    local count
    count=$(echo "$marketplaces" | jq 'length')
    print_success "Configured $count plugin marketplaces"
}

# --- Plugins ---
setup_plugins() {
    [[ -f "$PLUGINS_YAML" ]] || { print_warning "No plugins.yaml found"; return 0; }
    command -v yq >/dev/null 2>&1 || { print_warning "yq not found — skipping plugins"; return 0; }
    require_jq || return 0

    ensure_settings

    local plugins_json
    plugins_json=$(yq eval '.[]' "$PLUGINS_YAML" 2>/dev/null | while IFS= read -r plugin; do
        [[ -z "$plugin" || "$plugin" =~ ^# ]] && continue
        # If plugin already has @marketplace suffix, use as-is; otherwise default to @claude-plugins-official
        if [[ "$plugin" == *@* ]]; then
            printf '"%s": true\n' "$plugin"
        else
            printf '"%s@claude-plugins-official": true\n' "$plugin"
        fi
    done | jq -Rs '
        split("\n") | map(select(length > 0)) |
        map(split(": ") | {(.[0] | gsub("\""; "")): true}) |
        add // {}
    ')

    jq --argjson plugins "$plugins_json" '.enabledPlugins = $plugins' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

    local count
    count=$(echo "$plugins_json" | jq 'length')
    print_success "Enabled $count Claude Code plugins"
}

# --- MCP Servers (Claude Code) ---
setup_mcp() {
    [[ -f "$MCP_JSON" ]] || { print_info "No mcp.json found — skipping MCP setup"; return 0; }
    require_jq || return 0

    mkdir -p "$HOME/.claude"
    [[ -f "$CLAUDE_JSON" ]] || echo '{}' > "$CLAUDE_JSON"
    cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"

    local mcp_servers
    mcp_servers=$(jq '.mcpServers // {}' "$MCP_JSON")

    jq --argjson servers "$mcp_servers" '.mcpServers = ($servers + (.mcpServers // {}))' "$CLAUDE_JSON.bak" > "$CLAUDE_JSON"

    local count
    count=$(echo "$mcp_servers" | jq 'length')
    print_success "Configured $count MCP servers (Claude Code)"
}

# --- Claude Desktop (MCP servers + preferences) ---
setup_desktop() {
    require_jq || return 0

    local desktop_dir
    desktop_dir="$(dirname "$DESKTOP_CONFIG")"
    mkdir -p "$desktop_dir"
    [[ -f "$DESKTOP_CONFIG" ]] || echo '{}' > "$DESKTOP_CONFIG"
    cp "$DESKTOP_CONFIG" "$DESKTOP_CONFIG.bak"

    # Merge MCP servers (existing take precedence for project-local servers)
    if [[ -f "$MCP_JSON" ]]; then
        local mcp_servers
        mcp_servers=$(jq '.mcpServers // {}' "$MCP_JSON")
        jq --argjson servers "$mcp_servers" '.mcpServers = ($servers + (.mcpServers // {}))' "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"
        cp "$DESKTOP_CONFIG" "$DESKTOP_CONFIG.bak"

        local count
        count=$(echo "$mcp_servers" | jq 'length')
        print_success "Configured $count MCP servers (Claude Desktop)"
    fi

    # Merge preferences (always read from .bak to avoid read+write same file)
    if [[ -f "$DESKTOP_PREFS" ]]; then
        local prefs
        prefs=$(jq '.preferences // {}' "$DESKTOP_PREFS")
        jq --argjson prefs "$prefs" '.preferences = ($prefs + (.preferences // {}))' "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"

        local pref_count
        pref_count=$(echo "$prefs" | jq 'length')
        print_success "Configured $pref_count Desktop preferences"
    fi
}

# --- Hooks ---
setup_hooks() {
    [[ -f "$HOOKS_JSON" ]] || { print_info "No hooks.json found — skipping hooks"; return 0; }
    require_jq || return 0

    ensure_settings

    local hooks
    hooks=$(jq '.hooks // {}' "$HOOKS_JSON")

    jq --argjson hooks "$hooks" '.hooks = $hooks' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

    # Count hook events configured
    local events
    events=$(echo "$hooks" | jq 'keys | length')
    print_success "Configured $events hook events (format-on-save, notifications)"
}

# --- Voice + notification channel ---
setup_preferences() {
    [[ -f "$SETTINGS_FILE" ]] || return 0
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
    jq '.voiceEnabled = true | .preferredNotifChannel = "terminal_bell" | .defaultMode = "acceptEdits"' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_info "Voice mode + terminal bell + acceptEdits enabled"
}

# --- Main ---
setup_instructions
setup_marketplaces
setup_plugins
setup_mcp
setup_desktop
setup_hooks
setup_preferences
