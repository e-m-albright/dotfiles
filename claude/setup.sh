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
PLUGINS_YAML="$SCRIPT_DIR/plugins.yaml"

# Source print utils if available
if [[ -n "${print_section:-}" ]] || source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null; then
    :
fi

# --- System instructions (CLAUDE.md) ---
setup_instructions() {
    "$DOTFILES_DIR/macos/claude_instructions.sh" 2>/dev/null && \
        print_success "System instructions (~/.claude/CLAUDE.md)" || \
        print_warning "Could not update ~/.claude/CLAUDE.md"
}

# --- Plugins ---
setup_plugins() {
    if [[ ! -f "$PLUGINS_YAML" ]]; then
        print_warning "No plugins.yaml found at $PLUGINS_YAML"
        return 0
    fi

    # Require yq for YAML parsing
    if ! command -v yq >/dev/null 2>&1; then
        print_warning "yq not found — skipping plugin setup (brew install yq)"
        return 0
    fi
    if ! command -v jq >/dev/null 2>&1; then
        print_warning "jq not found — skipping plugin setup (brew install jq)"
        return 0
    fi

    mkdir -p "$HOME/.claude"
    [[ -f "$SETTINGS_FILE" ]] || echo '{}' > "$SETTINGS_FILE"

    # Backup
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"

    # Build enabledPlugins object from YAML list
    local plugins_json
    plugins_json=$(yq eval '.[]' "$PLUGINS_YAML" 2>/dev/null | while IFS= read -r plugin; do
        [[ -z "$plugin" || "$plugin" =~ ^# ]] && continue
        printf '"%s@claude-plugins-official": true\n' "$plugin"
    done | jq -Rs '
        split("\n") | map(select(length > 0)) |
        map(split(": ") | {(.[0] | gsub("\""; "")): true}) |
        add // {}
    ')

    # Merge into settings.json (preserves permissions and other keys)
    jq --argjson plugins "$plugins_json" '.enabledPlugins = $plugins' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

    local count
    count=$(echo "$plugins_json" | jq 'length')
    print_success "Enabled $count Claude Code plugins"
}

# --- Voice ---
setup_voice() {
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        return 0
    fi
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
    jq '.voiceEnabled = true' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_info "Voice mode enabled"
}

# --- Main ---
setup_instructions
setup_plugins
setup_voice
