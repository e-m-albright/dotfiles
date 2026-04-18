#!/usr/bin/env bash
# Configure Codex CLI: MCP servers, hooks, skills, agents, and global instructions.
# Idempotent — safe to run multiple times.
#
# Usage:
#   ./setup.sh                          # Full setup (personal profile)
#   ./setup.sh --work                   # Work profile
#   ./setup.sh --reset-mcp              # Reset managed MCP entries to dotfiles defaults
#   dotfiles agent-setup                # Via dotfiles CLI alias
#
# Codex CLI reads:
#   ~/.codex/config.toml                # Main config (TOML, not JSON)
#   ~/.codex/AGENTS.md                  # Global instructions
#   ~/.codex/hooks.json                 # Global hooks
#   ~/.codex/skills/                    # User-level skills
#   .codex/                             # Project-level config (optional)
#   AGENTS.md / CODEX.md                # Project-level instructions

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
CODEX_HOME="$HOME/.codex"
CONFIG_TOML="$CODEX_HOME/config.toml"
MCP_SKIP_FILE="$HOME/.config/dotfiles/mcp-skip"
PROFILE_FILE="$HOME/.config/dotfiles/profile"
RESET_MCP=false

# Parse flags
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

# Load persistent MCP skip list
if [[ -f "$MCP_SKIP_FILE" ]]; then
    file_skips=$(grep -v '^#' "$MCP_SKIP_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
    MCP_SKIP="${MCP_SKIP:+$MCP_SKIP,}$file_skips"
fi

# Source print utils
source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null || true

require_jq() {
    command -v jq >/dev/null 2>&1 || { print_warning "jq not found — skipping"; return 1; }
}

# Skip if codex isn't installed
if ! command -v codex >/dev/null 2>&1; then
    print_skip "Codex CLI not installed — skipping setup"
    return 0 2>/dev/null || exit 0
fi

mkdir -p "$CODEX_HOME"

# --- Global instructions (AGENTS.md) ---
setup_instructions() {
    local global_agents="$SHARED_DIR/rules.md"
    [[ -f "$global_agents" ]] || return 0

    # Codex reads ~/.codex/AGENTS.md for global instructions
    cat > "$CODEX_HOME/AGENTS.md" << AGENTS_EOF
# Global Agent Instructions

$(cat "$global_agents")

## Codex-Specific

- This project uses AGENTS.md as the primary instruction file.
- When CODEX.md exists at the project root, it is a symlink to AGENTS.md.
- Follow the same conventions as Claude Code: verify before claiming done, TDD when tests exist, minimize surface area.
AGENTS_EOF

    print_success "Global instructions (~/.codex/AGENTS.md)"
}

# --- MCP Servers (in config.toml) ---
# Codex uses TOML config with [mcp_servers.<name>] sections.
# We generate the MCP portion from shared mcp-servers.json, preserving
# any non-managed sections of config.toml.
setup_mcp() {
    [[ -f "$SHARED_DIR/mcp-servers.json" ]] || return 0
    require_jq || return 0

    local skip_json
    skip_json=$(if [[ -n "${MCP_SKIP:-}" ]]; then printf '%s' "$MCP_SKIP" | jq -Rc 'split(",")'; else echo '[]'; fi)

    # Generate TOML MCP server blocks from shared JSON
    local mcp_toml
    mcp_toml=$(jq -r --argjson skip "$skip_json" --arg profile "$DOTFILES_PROFILE" '
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index("codex") or index("claude")))
        | map(select(.value.profiles | index($profile)))
        | map(select(.key as $k | $skip | index($k) | not))
        | .[] | (
            "\n[mcp_servers.\(.key)]",
            if .value.url then "url = \"\(.value.url)\"" else empty end,
            if .value.command then "command = \"\(.value.command)\"" else empty end,
            if .value.args then "args = [\(.value.args | map("\"" + . + "\"") | join(", "))]" else empty end,
            "enabled = true"
        )
    ' "$SHARED_DIR/mcp-servers.json")

    local server_count
    server_count=$(jq --argjson skip "$skip_json" --arg profile "$DOTFILES_PROFILE" '
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index("codex") or index("claude")))
        | map(select(.value.profiles | index($profile)))
        | map(select(.key as $k | $skip | index($k) | not))
        | length
    ' "$SHARED_DIR/mcp-servers.json")

    # Preserve non-MCP config if config.toml already exists
    local existing_non_mcp=""
    if [[ -f "$CONFIG_TOML" ]]; then
        cp "$CONFIG_TOML" "$CONFIG_TOML.bak"
        # Extract everything before the first [mcp_servers.] section
        existing_non_mcp=$(sed '/^\[mcp_servers\./,$d' "$CONFIG_TOML" | sed '/^$/N;/^\n$/d')
    fi

    # Also add fallback filename config so Codex reads CODEX.md too
    cat > "$CONFIG_TOML" << CONFIG_EOF
# Codex CLI configuration
# AUTO-GENERATED by dotfiles agent-setup — edit agents/codex/setup.sh instead

# Read CODEX.md as fallback (scaffolded projects create CODEX.md → AGENTS.md symlink)
project_doc_fallback_filenames = ["CODEX.md"]

${existing_non_mcp}
# --- MCP Servers (managed by dotfiles) ---
${mcp_toml}
CONFIG_EOF

    print_success "Configured $server_count MCP servers (Codex) [profile: $DOTFILES_PROFILE]"
}

# --- Hooks ---
setup_hooks() {
    local hooks_source="$SCRIPT_DIR/hooks.json"
    [[ -f "$hooks_source" ]] || return 0

    cp "$hooks_source" "$CODEX_HOME/hooks.json"
    print_success "Deployed hooks (~/.codex/hooks.json)"
}

# --- Skills ---
setup_skills() {
    local skills_dir="$SCRIPT_DIR/skills"
    local dest_skills="$CODEX_HOME/skills"

    [[ -d "$skills_dir" ]] || return 0

    local skill_count=0
    for skill in "$skills_dir"/*/SKILL.md; do
        [[ -f "$skill" ]] || continue
        local skill_name
        skill_name="$(basename "$(dirname "$skill")")"
        mkdir -p "$dest_skills/$skill_name"
        cp "$skill" "$dest_skills/$skill_name/SKILL.md"
        skill_count=$((skill_count + 1))
    done

    if [[ $skill_count -gt 0 ]]; then
        print_success "Deployed $skill_count skills (~/.codex/skills/)"
    fi
}

# --- Agents ---
setup_agents() {
    local agents_dir="$SCRIPT_DIR/agents"
    [[ -d "$agents_dir" ]] || return 0

    local dest_agents="$CODEX_HOME/agents"
    mkdir -p "$dest_agents"

    local agent_count=0
    for agent in "$agents_dir"/*.md; do
        [[ -f "$agent" ]] || continue
        cp "$agent" "$dest_agents/"
        agent_count=$((agent_count + 1))
    done

    if [[ $agent_count -gt 0 ]]; then
        print_success "Deployed $agent_count agents (~/.codex/agents/)"
    fi
}

# --- Main ---
setup_instructions
setup_mcp
setup_hooks
setup_skills
setup_agents
