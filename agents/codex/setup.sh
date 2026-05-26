#!/usr/bin/env bash
# Configure Codex CLI: MCP servers, hooks, command auto-approve rules, skills,
# subagents, and global instructions. Idempotent.
#
# Usage:
#   ./setup.sh                          # Full setup
#   ./setup.sh --reset-mcp              # Reset managed MCP entries to dotfiles defaults
#   dotfiles agent-setup                # Via dotfiles CLI alias
#
# Codex CLI reads:
#   ~/.codex/config.toml                # Main config (TOML, not JSON)
#   ~/.codex/AGENTS.md                  # Global instructions
#   ~/.codex/hooks.json                 # Global hooks
#   ~/.codex/rules/default.rules        # Command auto-approve allowlist
#   ~/.codex/agents/*.md                # Subagents
#   ~/.agents/skills/                   # Shared skills (deployed via npx skills)

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
CODEX_HOME="$HOME/.codex"
CONFIG_TOML="$CODEX_HOME/config.toml"
STATUSLINE_TOML="$SCRIPT_DIR/statusline.toml"

source "$SHARED_DIR/lib.sh"
agentlib_init "$@"

if ! command -v codex >/dev/null 2>&1; then
    print_skip "Codex CLI not installed — skipping setup"
    return 0 2>/dev/null || exit 0
fi

mkdir -p "$CODEX_HOME"

# --- Global instructions (AGENTS.md) — includes baked rules ---
# shellcheck source=../shared/bake-rules.sh
source "$SHARED_DIR/bake-rules.sh"
setup_instructions() {
    local global_agents="$SHARED_DIR/rules.md"
    [[ -f "$global_agents" ]] || return 0

    {
        echo "# Global Agent Instructions"
        echo ""
        cat "$global_agents"
        echo ""
        echo "## Codex-Specific"
        echo ""
        echo "- This project uses AGENTS.md as the primary instruction file."
        echo "- When CODEX.md exists at the project root, it is a symlink to AGENTS.md."
        echo "- Follow the same conventions as Claude Code: verify before claiming done, TDD when tests exist, minimize surface area."
        bake_rules "$DOTFILES_DIR"
    } > "$CODEX_HOME/AGENTS.md"

    local rule_count
    rule_count=$(find "$DOTFILES_DIR/.ai/rules/process" -maxdepth 1 -name '*.mdc' 2>/dev/null | wc -l | tr -d ' ')
    print_success "Global instructions + $rule_count baked rules (~/.codex/AGENTS.md)"
}

# --- Command auto-approve rules (~/.codex/rules/default.rules) ---
# Codex appends interactively-approved one-offs to this file; dotfiles owns the
# baseline. We refuse to overwrite if the live file is larger than ours (likely
# contains user additions not yet folded back) — instead, we leave a marker.
setup_default_rules() {
    local src="$SCRIPT_DIR/default.rules"
    local dest="$CODEX_HOME/rules/default.rules"
    [[ -f "$src" ]] || return 0
    mkdir -p "$CODEX_HOME/rules"

    if [[ -f "$dest" ]] && [[ "$(wc -l < "$dest")" -gt "$(wc -l < "$src")" ]] \
       && ! cmp -s "$src" "$dest"; then
        print_info "~/.codex/rules/default.rules has more lines than dotfiles baseline — leaving in place."
        print_step "Fold new universal rules back into agents/codex/default.rules, then re-run."
        return 0
    fi

    cp "$src" "$dest"
    local n
    n=$(grep -c '^prefix_rule' "$dest" 2>/dev/null || echo 0)
    print_success "Deployed $n command auto-approve rules (~/.codex/rules/default.rules)"
}

# --- MCP Servers (in config.toml) ---
setup_mcp() {
    [[ -f "$SHARED_MCP_JSON" ]] || return 0
    require_jq || return 0

    local skip_json
    skip_json=$(mcp_skip_json)

    # Generate TOML [mcp_servers.<name>] blocks for codex + claude targets
    # (we keep claude as a fallback target so the same servers reach Codex
    # without a dedicated `codex` target, matching prior behavior).
    local mcp_toml
    mcp_toml=$(jq -r --argjson skip "$skip_json" '
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index("codex") or index("claude")))
        | map(select(.key as $k | $skip | index($k) | not))
        | .[] | (
            "\n[mcp_servers.\(.key)]",
            if .value.url then "url = \"\(.value.url)\"" else empty end,
            if .value.command then "command = \"\(.value.command)\"" else empty end,
            if .value.args then "args = [\(.value.args | map("\"" + . + "\"") | join(", "))]" else empty end,
            "enabled = true"
        )
    ' "$SHARED_MCP_JSON")

    local server_count
    server_count=$(jq --argjson skip "$skip_json" '
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index("codex") or index("claude")))
        | map(select(.key as $k | $skip | index($k) | not))
        | length
    ' "$SHARED_MCP_JSON")

    [[ -f "$CONFIG_TOML" ]] && cp "$CONFIG_TOML" "$CONFIG_TOML.bak"

    # Preserve non-managed sections (marketplaces, projects, plugins, tui, etc.)
    local preserved_sections=""
    if [[ -f "$CONFIG_TOML.bak" ]]; then
        preserved_sections=$(awk '
            /^# Codex CLI configuration/,/^# --- MCP Servers/ { next }
            /^\[mcp_servers\./ { skip=1; next }
            /^\[/ && !/^\[mcp_servers\./ { skip=0 }
            !skip { print }
        ' "$CONFIG_TOML.bak" | sed '/^project_doc_fallback_filenames/d' | sed '/^$/N;/^\n$/d')
    fi

    cat > "$CONFIG_TOML" << CONFIG_EOF
# Codex CLI configuration
# Managed section — AUTO-GENERATED by dotfiles agent-setup
# Non-managed sections (marketplaces, projects, etc.) are preserved below

# Read CODEX.md as fallback (scaffolded projects create CODEX.md → AGENTS.md symlink)
project_doc_fallback_filenames = ["CODEX.md"]

# --- MCP Servers (managed by dotfiles) ---
${mcp_toml}
CONFIG_EOF

    if [[ -n "$preserved_sections" ]]; then
        printf '\n# --- Codex-managed (not dotfiles) ---\n' >> "$CONFIG_TOML"
        printf '%s\n' "$preserved_sections" >> "$CONFIG_TOML"
    fi

    print_success "Configured $server_count MCP servers (Codex)"
}

# --- Hooks ---
setup_hooks() {
    local src="$SCRIPT_DIR/hooks.json"
    [[ -f "$src" ]] || return 0
    cp "$src" "$CODEX_HOME/hooks.json"
    print_success "Deployed hooks (~/.codex/hooks.json)"
}

# --- Statusline ---
setup_statusline() {
    [[ -f "$STATUSLINE_TOML" ]] || return 0
    [[ -f "$CONFIG_TOML" ]] || touch "$CONFIG_TOML"
    cp "$CONFIG_TOML" "$CONFIG_TOML.bak"

    awk -v statusline_toml="$STATUSLINE_TOML" '
        function emit_statusline() {
            while ((getline line < statusline_toml) > 0) { print line }
            close(statusline_toml); inserted = 1
        }
        skip_statusline_array { if ($0 ~ /\]/) skip_statusline_array = 0; next }
        /^\[/ {
            in_tui = ($0 == "[tui]")
            print
            if (in_tui) emit_statusline()
            next
        }
        in_tui && /^[[:space:]]*(theme|status_line)[[:space:]]*=/ {
            if ($0 ~ /^[[:space:]]*status_line[[:space:]]*=/ && $0 !~ /\]/) skip_statusline_array = 1
            next
        }
        { print }
        END { if (!inserted) { print ""; print "[tui]"; emit_statusline() } }
    ' "$CONFIG_TOML.bak" > "$CONFIG_TOML"

    print_success "Configured Codex statusline (~/.codex/config.toml)"
}

setup_instructions
setup_default_rules
setup_mcp
setup_statusline
setup_hooks
deploy_skills codex
deploy_subagents "$CODEX_HOME/agents"
