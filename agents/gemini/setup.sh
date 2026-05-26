#!/usr/bin/env bash
# Configure Gemini CLI: settings, MCP servers, global instructions.
# Idempotent — safe to run multiple times.
#
# Gemini CLI reads:
#   ~/.gemini/settings.json   # main config (incl. mcpServers, security.auth)
#   ~/.gemini/GEMINI.md       # global instructions
#   <project>/GEMINI.md       # project-level instructions
#
# Gemini has no first-class skills / subagents surface yet. We deploy the same
# baked rules as Codex/Pi (single global instructions file).

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
GEMINI_HOME="$HOME/.gemini"
SETTINGS_FILE="$GEMINI_HOME/settings.json"

source "$SHARED_DIR/lib.sh"
agentlib_init "$@"

if ! command -v gemini >/dev/null 2>&1; then
    print_skip "Gemini CLI not installed — skipping setup"
    return 0 2>/dev/null || exit 0
fi

mkdir -p "$GEMINI_HOME"

# --- Settings + MCP servers (merge into ~/.gemini/settings.json) ---
setup_settings_and_mcp() {
    require_jq || return 0

    if [[ ! -f "$SETTINGS_FILE" ]]; then
        cp "$SCRIPT_DIR/settings.json" "$SETTINGS_FILE"
    fi
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"

    [[ -f "$SHARED_MCP_JSON" ]] || { print_info "No shared mcp-servers.json"; return 0; }

    local managed_keys mcp_servers
    managed_keys=$(mcp_managed_keys gemini)
    mcp_servers=$(mcp_servers_for gemini)

    if [[ "$RESET_MCP" == "true" ]]; then
        jq --argjson managed "$managed_keys" --argjson servers "$mcp_servers" '
            .mcpServers = (
                ((.mcpServers // {}) | with_entries(select(.key as $k | ($managed | index($k) | not))))
                + $servers
            )
        ' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    else
        jq --argjson servers "$mcp_servers" '.mcpServers = ((.mcpServers // {}) + $servers)' \
            "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    fi

    local count
    count=$(echo "$mcp_servers" | jq 'length')
    print_success "Configured $count MCP servers (Gemini)"
}

# --- Global instructions (GEMINI.md) — baked rules, same source as Codex/Pi ---
setup_instructions() {
    local global_rules="$SHARED_DIR/rules.md"
    [[ -f "$global_rules" ]] || return 0

    # shellcheck source=../shared/bake-rules.sh
    source "$SHARED_DIR/bake-rules.sh"
    {
        echo "# Global Agent Instructions"
        echo ""
        cat "$global_rules"
        echo ""
        bake_rules "$DOTFILES_DIR"
    } > "$GEMINI_HOME/GEMINI.md"

    local rule_count
    rule_count=$(find "$DOTFILES_DIR/.ai/rules/process" -maxdepth 1 -name '*.mdc' 2>/dev/null | wc -l | tr -d ' ')
    print_success "Global instructions + $rule_count baked rules (~/.gemini/GEMINI.md)"
}

setup_settings_and_mcp
setup_instructions
