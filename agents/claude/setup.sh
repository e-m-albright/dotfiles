#!/usr/bin/env bash
# Configure Claude Code: instructions, plugins, MCP servers, permissions, hooks,
# skills, subagents, rules. Idempotent.
#
# Usage:
#   ./setup.sh                          # Full setup
#   ./setup.sh --clean                  # Remove nonconforming plugins/MCPs/projects
#   ./setup.sh --reset-mcp              # Reset managed MCP entries to dotfiles defaults
#   dotfiles agent-setup                # Via dotfiles CLI alias
#   MCP_SKIP=granola ./setup.sh         # Skip specific MCP servers
#
# Sources of truth in this repo:
#   global-claude.md     →  ~/.claude/CLAUDE.md
#   plugins.yaml         →  settings.json:.enabledPlugins
#   marketplaces.json    →  settings.json:.extraKnownMarketplaces
#   permissions.json     →  settings.json:.permissions.{allow,deny,defaultMode}
#   hooks.json           →  settings.json:.hooks
#   ../shared/mcp-servers.json (claude target) → ~/.claude.json:.mcpServers
#                                              → ~/Library/.../claude_desktop_config.json
#   ../../.ai/skills     →  ~/.claude/skills/* (via npx skills)
#   ../../.ai/agents     →  ~/.claude/agents/*.md
#   ../../.ai/rules/process →  ~/.claude/rules/*.md (symlinks)

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
SETTINGS_FILE="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"
DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

PLUGINS_YAML="$SCRIPT_DIR/plugins.yaml"
HOOKS_JSON="$SCRIPT_DIR/hooks.json"
GLOBAL_CLAUDE_MD="$SCRIPT_DIR/global-claude.md"
DESKTOP_PREFS="$SCRIPT_DIR/desktop-preferences.json"
MARKETPLACES_JSON="$SCRIPT_DIR/marketplaces.json"
PERMISSIONS_JSON="$SCRIPT_DIR/permissions.json"

source "$SHARED_DIR/lib.sh"
agentlib_init "$@"

# --- Settings file helper ---
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
    [[ -f "$MARKETPLACES_JSON" ]] || return 0
    require_jq || return 0
    ensure_settings

    local marketplaces
    marketplaces=$(jq '. // {}' "$MARKETPLACES_JSON")
    jq --argjson mkts "$marketplaces" '.extraKnownMarketplaces = $mkts' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_success "Configured $(echo "$marketplaces" | jq 'length') plugin marketplaces"
}

# --- Plugins ---
setup_plugins() {
    [[ -f "$PLUGINS_YAML" ]] || return 0
    require_cmd yq || return 0
    require_jq || return 0
    ensure_settings

    local plugins_json
    plugins_json=$(yq eval '.[]' "$PLUGINS_YAML" 2>/dev/null | while IFS= read -r plugin; do
        [[ -z "$plugin" || "$plugin" =~ ^# ]] && continue
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
    print_success "Enabled $(echo "$plugins_json" | jq 'length') Claude Code plugins"
}

# --- Permissions (allow / deny / defaultMode) ---
# Dotfiles is the canonical source for the baseline allow/deny lists. If you
# approve a new permission interactively in Claude Code, periodically fold it
# back into permissions.json. This setup *replaces* the lists wholesale.
setup_permissions() {
    [[ -f "$PERMISSIONS_JSON" ]] || return 0
    require_jq || return 0
    ensure_settings

    jq --slurpfile perms "$PERMISSIONS_JSON" '
        .permissions = ((.permissions // {})
            + {
                allow: $perms[0].allow,
                deny:  $perms[0].deny,
                defaultMode: ($perms[0].defaultMode // (.permissions.defaultMode // "auto"))
            })
    ' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"

    local a d
    a=$(jq '.allow | length' "$PERMISSIONS_JSON")
    d=$(jq '.deny  | length' "$PERMISSIONS_JSON")
    print_success "Permissions: $a allow, $d deny (~/.claude/settings.json)"
}

# --- MCP Servers (Claude Code, ~/.claude.json) ---
setup_mcp() {
    [[ -f "$SHARED_MCP_JSON" ]] || return 0
    require_jq || return 0

    mkdir -p "$HOME/.claude"
    [[ -f "$CLAUDE_JSON" ]] || echo '{}' > "$CLAUDE_JSON"
    cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"

    local managed_keys mcp_servers
    managed_keys=$(mcp_managed_keys claude)
    mcp_servers=$(mcp_servers_for claude)

    if [[ "$RESET_MCP" == "true" ]]; then
        jq --argjson managed "$managed_keys" --argjson servers "$mcp_servers" '
            .mcpServers = (
                ((.mcpServers // {}) | with_entries(select(.key as $k | ($managed | index($k) | not))))
                + $servers
            )
        ' "$CLAUDE_JSON.bak" > "$CLAUDE_JSON"
        print_info "MCP reset (--reset-mcp): managed shared entries refreshed"
    else
        jq --argjson servers "$mcp_servers" '.mcpServers = ((.mcpServers // {}) + $servers)' \
            "$CLAUDE_JSON.bak" > "$CLAUDE_JSON"
    fi

    print_success "Configured $(echo "$mcp_servers" | jq 'length') MCP servers (Claude Code)"
}

# --- Claude Desktop (MCP + preferences) ---
setup_desktop() {
    require_jq || return 0

    mkdir -p "$(dirname "$DESKTOP_CONFIG")"
    [[ -f "$DESKTOP_CONFIG" ]] || echo '{}' > "$DESKTOP_CONFIG"
    cp "$DESKTOP_CONFIG" "$DESKTOP_CONFIG.bak"

    if [[ -f "$SHARED_MCP_JSON" ]]; then
        local skip_json
        skip_json=$(mcp_skip_json)

        # Desktop accepts both "claude" and "desktop" targets, and needs http
        # servers rewritten as `npx -y mcp-remote <url>` stdio bridges.
        local managed_keys
        managed_keys=$(jq '[
            to_entries
            | map(select(.value | type == "object"))
            | map(select(.value.targets | (index("claude") or index("desktop"))))
            | .[].key
        ]' "$SHARED_MCP_JSON")

        local mcp_servers
        mcp_servers=$(jq --argjson skip "$skip_json" '
            to_entries
            | map(select(.value | type == "object"))
            | map(select(.value.targets | (index("claude") or index("desktop"))))
            | map(select(.key as $k | $skip | index($k) | not))
            | map({
                key: .key,
                value: (
                    .value
                    | del(.targets)
                    | if .type == "http" and (.url? != null) then
                        {
                            command: "npx",
                            args: (
                                ["-y", "mcp-remote", .url]
                                + ((.headers // {}) | to_entries | map("--header=\(.key):\(.value)"))
                            )
                        }
                      else . end
                )
            })
            | from_entries
        ' "$SHARED_MCP_JSON")

        if [[ "$RESET_MCP" == "true" ]]; then
            jq --argjson managed "$managed_keys" --argjson servers "$mcp_servers" '
                .mcpServers = (
                    ((.mcpServers // {}) | with_entries(select(.key as $k | ($managed | index($k) | not))))
                    + $servers
                )
            ' "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"
        else
            jq --argjson servers "$mcp_servers" '.mcpServers = ((.mcpServers // {}) + $servers)' \
                "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"
        fi
        cp "$DESKTOP_CONFIG" "$DESKTOP_CONFIG.bak"
        print_success "Configured $(echo "$mcp_servers" | jq 'length') MCP servers (Claude Desktop)"
    fi

    if [[ -f "$DESKTOP_PREFS" ]]; then
        local prefs
        prefs=$(jq '.preferences // {}' "$DESKTOP_PREFS")
        jq --argjson prefs "$prefs" '.preferences = ($prefs + (.preferences // {}))' \
            "$DESKTOP_CONFIG.bak" > "$DESKTOP_CONFIG"
        print_success "Configured $(echo "$prefs" | jq 'length') Desktop preferences"
    fi
}

# --- Hooks ---
setup_hooks() {
    [[ -f "$HOOKS_JSON" ]] || return 0
    require_jq || return 0
    ensure_settings

    local hooks
    hooks=$(jq '.hooks // {}' "$HOOKS_JSON")
    jq --argjson hooks "$hooks" '.hooks = $hooks' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_success "Configured $(echo "$hooks" | jq 'keys | length') hook events"
}

# --- Statusline ---
setup_statusline() {
    local src="$SCRIPT_DIR/statusline.sh"
    [[ -f "$src" ]] || return 0
    require_jq || return 0
    chmod +x "$src"
    ensure_settings
    jq --arg cmd "$src" '.statusLine = {type: "command", command: $cmd}' \
        "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_success "Statusline configured"
}

# --- Voice + notification preferences ---
setup_preferences() {
    [[ -f "$SETTINGS_FILE" ]] || return 0
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
    jq '.voiceEnabled = true | .preferredNotifChannel = "terminal_bell" | .defaultMode = "acceptEdits"' \
        "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
    print_info "Voice mode + terminal bell + acceptEdits enabled"
}

# --- Skills (local + external) ---
setup_skills() {
    deploy_skills claude-code

    local ext_skills="$SCRIPT_DIR/external-skills.txt"
    [[ -f "$ext_skills" ]] || return 0
    require_cmd npx || return 0

    local ext_count=0 ext_installed=0
    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        ext_count=$((ext_count + 1))
        local skill_name="${line##*@}"
        if [[ -d "$HOME/.agents/skills/$skill_name" ]] || [[ -d "$HOME/.claude/skills/$skill_name" ]]; then
            continue
        fi
        npx skills add "$line" -g -y >/dev/null 2>&1 && ext_installed=$((ext_installed + 1))
    done < "$ext_skills"
    [[ $ext_installed -gt 0 ]] && print_success "Installed $ext_installed external skills"
    print_info "$ext_count external skills tracked (external-skills.txt)"
}

# --- Clean (remove drifted plugins / marketplaces / MCP perms / stale projects) ---
setup_clean() {
    $CLEAN_MODE || return 0
    require_jq || return 0

    print_section "Cleaning nonconforming config"

    local expected_plugins
    expected_plugins=$(yq eval '.[]' "$PLUGINS_YAML" 2>/dev/null | while IFS= read -r plugin; do
        [[ -z "$plugin" || "$plugin" =~ ^# ]] && continue
        if [[ "$plugin" == *@* ]]; then printf '%s\n' "$plugin"
        else printf '%s@claude-plugins-official\n' "$plugin"
        fi
    done)

    if [[ -f "$SETTINGS_FILE" ]]; then
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
        local current_plugins removed_plugins=0
        current_plugins=$(jq -r '.enabledPlugins // {} | keys[]' "$SETTINGS_FILE")
        for plugin in $current_plugins; do
            echo "$expected_plugins" | grep -qxF "$plugin" || {
                print_step "Removing plugin: $plugin"
                removed_plugins=$((removed_plugins + 1))
            }
        done
        local keep_json
        keep_json=$(echo "$expected_plugins" | jq -Rn '[inputs | select(length > 0)] | map({(.): true}) | add // {}')
        jq --argjson keep "$keep_json" '.enabledPlugins = $keep' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
        print_success "Removed $removed_plugins nonconforming plugins"

        cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
        local expected_mkts removed_mkts=0
        expected_mkts=$(jq -r 'keys[]' "$MARKETPLACES_JSON" 2>/dev/null)
        for mkt in $(jq -r '.extraKnownMarketplaces // {} | keys[]' "$SETTINGS_FILE"); do
            echo "$expected_mkts" | grep -qxF "$mkt" || {
                print_step "Removing marketplace: $mkt"
                removed_mkts=$((removed_mkts + 1))
            }
        done
        local keep_mkts
        keep_mkts=$(jq '. // {}' "$MARKETPLACES_JSON")
        jq --argjson mkts "$keep_mkts" '.extraKnownMarketplaces = $mkts' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
        print_success "Removed $removed_mkts nonconforming marketplaces"

        # Stale MCP permission grants (mcp__*)
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
        local expected_mcp_names removed_perms=0
        expected_mcp_names=$(jq -r 'keys[]' "$SHARED_MCP_JSON" 2>/dev/null)
        local allow_json cleaned_allow="[]"
        allow_json=$(jq -r '.permissions.allow // [] | .[]' "$SETTINGS_FILE")
        while IFS= read -r perm; do
            [[ -z "$perm" ]] && continue
            if [[ "$perm" =~ ^mcp__plugin_ ]]; then
                local plugin_part="${perm#mcp__plugin_}"
                local plugin_name="${plugin_part%%_*}"
                local plugin_lower
                plugin_lower=$(echo "$plugin_name" | tr '[:upper:]' '[:lower:]')
                local found=false
                while IFS= read -r ep; do
                    local ep_lower
                    ep_lower=$(echo "${ep%%@*}" | tr '[:upper:]' '[:lower:]')
                    [[ "$ep_lower" == "$plugin_lower" ]] && { found=true; break; }
                done <<< "$expected_plugins"
                $found || { print_step "Removing plugin MCP permission: $perm"; removed_perms=$((removed_perms + 1)); continue; }
            elif [[ "$perm" =~ ^mcp__ ]]; then
                local server_name="${perm#mcp__}"
                echo "$expected_mcp_names" | grep -qxF "$server_name" || {
                    print_step "Removing MCP permission: $perm"
                    removed_perms=$((removed_perms + 1))
                    continue
                }
            fi
            cleaned_allow=$(echo "$cleaned_allow" | jq --arg p "$perm" '. + [$p]')
        done <<< "$allow_json"
        jq --argjson perms "$cleaned_allow" '.permissions.allow = $perms' "$SETTINGS_FILE.bak" > "$SETTINGS_FILE"
        [[ $removed_perms -gt 0 ]] && print_success "Removed $removed_perms stale MCP permissions"
    fi

    # Stale project entries in ~/.claude.json
    if [[ -f "$CLAUDE_JSON" ]]; then
        cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"
        local removed_projects=0
        local project_paths
        project_paths=$(jq -r '.projects // {} | keys[]' "$CLAUDE_JSON")
        while IFS= read -r proj_path; do
            [[ -z "$proj_path" ]] && continue
            if [[ ! -d "$proj_path" ]]; then
                print_step "Removing stale project: $proj_path"
                jq --arg p "$proj_path" 'del(.projects[$p])' "$CLAUDE_JSON" > "$CLAUDE_JSON.tmp"
                mv "$CLAUDE_JSON.tmp" "$CLAUDE_JSON"
                removed_projects=$((removed_projects + 1))
            fi
        done <<< "$project_paths"
        print_success "Removed $removed_projects stale project entries"
    fi
}

print_manual_steps() {
    if ! jq -e '.enabledPlugins["codex@openai-codex"]' "$SETTINGS_FILE" >/dev/null 2>&1; then
        if grep -q '# - codex@openai-codex' "$PLUGINS_YAML" 2>/dev/null; then
            print_info "Codex plugin (run inside Claude Code):"
            print_step "/plugin marketplace add openai/codex-plugin-cc"
            print_step "/plugin install codex@openai-codex"
            print_step "/codex:setup"
        fi
    fi
}

setup_clean
setup_instructions
setup_marketplaces
setup_plugins
setup_permissions
setup_mcp
setup_desktop
setup_hooks
setup_skills
deploy_subagents "$HOME/.claude/agents"
symlink_process_rules "$HOME/.claude/rules" .md
setup_statusline
setup_preferences
print_manual_steps
