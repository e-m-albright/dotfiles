#!/usr/bin/env bash
# Configure Claude Code: plugins, MCP servers, voice, and system instructions.
# Idempotent — safe to run multiple times.
#
# Usage:
#   ./setup.sh                          # Full setup (personal profile)
#   ./setup.sh --work                   # Work profile
#   dotfiles claude-setup               # Via dotfiles CLI alias
#   dotfiles claude-setup --work        # Work profile via CLI
#   MCP_SKIP=granola ./setup.sh         # Skip specific MCP servers
#
# Profiles control which MCP servers are deployed:
#   personal (default): context7, playwright, granola
#   work:               context7, playwright, datadog, notion, linear
#
# Persistent config: ~/.config/dotfiles/profile   (contains "personal" or "work")
#                     ~/.config/dotfiles/mcp-skip  (one server name per line)
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
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETTINGS_FILE="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"
DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
PLUGINS_YAML="$SCRIPT_DIR/plugins.yaml"
HOOKS_JSON="$SCRIPT_DIR/hooks.json"
GLOBAL_CLAUDE_MD="$SCRIPT_DIR/global-claude.md"
DESKTOP_PREFS="$SCRIPT_DIR/desktop-preferences.json"
MARKETPLACES_JSON="$SCRIPT_DIR/marketplaces.json"
MCP_SKIP_FILE="$HOME/.config/dotfiles/mcp-skip"
PROFILE_FILE="$HOME/.config/dotfiles/profile"

# Parse --work / --personal flag
DOTFILES_PROFILE="${DOTFILES_PROFILE:-}"
for arg in "$@"; do
    case "$arg" in
        --work) DOTFILES_PROFILE="work" ;;
        --personal) DOTFILES_PROFILE="personal" ;;
    esac
done

# Fall back to persistent profile file, then default to "personal"
if [[ -z "$DOTFILES_PROFILE" ]] && [[ -f "$PROFILE_FILE" ]]; then
    DOTFILES_PROFILE=$(head -1 "$PROFILE_FILE" | tr -d '[:space:]')
fi
DOTFILES_PROFILE="${DOTFILES_PROFILE:-personal}"
export DOTFILES_PROFILE

# Load persistent MCP skip list (one server per line), merge with MCP_SKIP env var
if [[ -f "$MCP_SKIP_FILE" ]]; then
    file_skips=$(grep -v '^#' "$MCP_SKIP_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
    MCP_SKIP="${MCP_SKIP:+$MCP_SKIP,}$file_skips"
fi

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

    jq --argjson mkts "$marketplaces" '.extraKnownMarketplaces = $mkts' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

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
    local shared_mcp="$DOTFILES_DIR/agents/shared/mcp-servers.json"
    [[ -f "$shared_mcp" ]] || { print_info "No shared mcp-servers.json — skipping MCP setup"; return 0; }
    require_jq || return 0

    mkdir -p "$HOME/.claude"
    [[ -f "$CLAUDE_JSON" ]] || echo '{}' > "$CLAUDE_JSON"
    cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"

    # Filter by target, profile, and skip list; strip metadata fields
    local skip_json
    skip_json=$(if [[ -n "${MCP_SKIP:-}" ]]; then printf '%s' "$MCP_SKIP" | jq -Rc 'split(",")'; else echo '[]'; fi)

    local mcp_servers
    mcp_servers=$(jq --argjson skip "$skip_json" --arg profile "$DOTFILES_PROFILE" '
        to_entries
        | map(select(.value.targets | index("claude")))
        | map(select(.value.profiles | index($profile)))
        | map(select(.key as $k | $skip | index($k) | not))
        | map({key: .key, value: (.value | del(.targets, .profiles))})
        | from_entries
    ' "$shared_mcp")

    jq --argjson servers "$mcp_servers" '.mcpServers = ((.mcpServers // {}) + $servers)' "$CLAUDE_JSON.bak" > "$CLAUDE_JSON"

    local count
    count=$(echo "$mcp_servers" | jq 'length')
    print_success "Configured $count MCP servers (Claude Code) [profile: $DOTFILES_PROFILE]"
}

# --- Claude Desktop (MCP servers + preferences) ---
setup_desktop() {
    require_jq || return 0

    local desktop_dir
    desktop_dir="$(dirname "$DESKTOP_CONFIG")"
    mkdir -p "$desktop_dir"
    [[ -f "$DESKTOP_CONFIG" ]] || echo '{}' > "$DESKTOP_CONFIG"
    cp "$DESKTOP_CONFIG" "$DESKTOP_CONFIG.bak"

    # Merge MCP servers from shared source (servers targeting "claude" or "desktop")
    if [[ -f "$DOTFILES_DIR/agents/shared/mcp-servers.json" ]]; then
        local skip_json
        skip_json=$(if [[ -n "${MCP_SKIP:-}" ]]; then printf '%s' "$MCP_SKIP" | jq -Rc 'split(",")'; else echo '[]'; fi)

        local mcp_servers
        mcp_servers=$(jq --argjson skip "$skip_json" --arg profile "$DOTFILES_PROFILE" '
            to_entries
            | map(select(.value.targets | (index("claude") or index("desktop"))))
            | map(select(.value.profiles | index($profile)))
            | map(select(.key as $k | $skip | index($k) | not))
            | map({key: .key, value: (.value | del(.targets, .profiles))})
            | from_entries
        ' "$DOTFILES_DIR/agents/shared/mcp-servers.json")
        jq --argjson servers "$mcp_servers" '.mcpServers = ((.mcpServers // {}) + $servers)' "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"
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

# --- Skills & Agents ---
setup_skills_and_agents() {
    local skills_dir="$SCRIPT_DIR/skills"
    local agents_dir="$SCRIPT_DIR/agents"
    local dest_skills="$HOME/.claude/skills"
    local dest_agents="$HOME/.claude/agents"

    # Deploy local skills (from dotfiles)
    if [[ -d "$skills_dir" ]]; then
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
            print_success "Deployed $skill_count local skills (~/.claude/skills/)"
        fi
    fi

    # Install external skills (from npx skills ecosystem)
    local ext_skills="$SCRIPT_DIR/external-skills.txt"
    if [[ -f "$ext_skills" ]] && command -v npx >/dev/null 2>&1; then
        local ext_count=0
        local ext_installed=0
        while IFS= read -r line; do
            [[ -z "$line" || "$line" =~ ^# ]] && continue
            ext_count=$((ext_count + 1))
            local skill_name
            skill_name="${line##*@}"
            if [[ -d "$dest_skills/$skill_name" ]]; then
                continue
            fi
            npx skills add "$line" -g -y >/dev/null 2>&1 && ext_installed=$((ext_installed + 1))
        done < "$ext_skills"
        if [[ $ext_installed -gt 0 ]]; then
            print_success "Installed $ext_installed external skills (npx skills)"
        fi
        print_info "$ext_count external skills tracked (external-skills.txt)"
    fi

    # Deploy agents
    if [[ -d "$agents_dir" ]]; then
        local agent_count=0
        mkdir -p "$dest_agents"
        for agent in "$agents_dir"/*.md; do
            [[ -f "$agent" ]] || continue
            cp "$agent" "$dest_agents/"
            agent_count=$((agent_count + 1))
        done
        if [[ $agent_count -gt 0 ]]; then
            print_success "Deployed $agent_count agents (~/.claude/agents/)"
        fi
    fi
}

# --- Universal rules (symlinked to dotfiles) ---
setup_universal_rules() {
    local rules_source="$DOTFILES_DIR/.ai/rules/process"
    local rules_dest="$HOME/.claude/rules"

    [[ -d "$rules_source" ]] || { print_warning "No process rules found at $rules_source"; return 0; }

    mkdir -p "$rules_dest"

    local count=0
    for rule in "$rules_source"/*.mdc; do
        [[ -f "$rule" ]] || continue
        local rule_name
        rule_name="$(basename "$rule")"
        local dest="$rules_dest/$rule_name"

        if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$rule" ]]; then
            continue
        fi

        ln -sf "$rule" "$dest"
        count=$((count + 1))
    done

    local total
    total=$(find "$rules_source" -name '*.mdc' -type f | wc -l | tr -d ' ')
    print_success "Symlinked $total universal rules (~/.claude/rules/ → dotfiles)"
}

# --- Main ---
setup_instructions
setup_marketplaces
setup_plugins
setup_mcp
setup_desktop
setup_hooks
setup_skills_and_agents
setup_universal_rules
setup_preferences
