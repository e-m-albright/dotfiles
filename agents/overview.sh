#!/usr/bin/env bash
# Agentic setup overview — reports what's active across Claude Code and Cursor.
# Called by: dotfiles agents

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
source "$DOTFILES_DIR/macos/print_utils.sh"

# Deployed config locations
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"

# Source config locations
SHARED_MCP="$SCRIPT_DIR/shared/mcp-servers.json"

has_jq() { command -v jq >/dev/null 2>&1; }

# --- Section: MCP Servers ---
section_mcp() {
    print_section "MCP Servers"
    has_jq || { print_warning "jq required"; return; }
    [[ -f "$SHARED_MCP" ]] || { print_warning "No shared MCP config found"; return; }

    printf "  %-15s %-10s %-10s\n" "Server" "Claude" "Cursor"
    printf "  %-15s %-10s %-10s\n" "───────" "──────" "──────"
    jq -r 'to_entries[] | "\(.key) \(.value.targets | join(","))"' "$SHARED_MCP" | \
    while read -r name targets; do
        local claude_mark="—" cursor_mark="—"
        [[ "$targets" == *claude* ]] && claude_mark="✓"
        [[ "$targets" == *cursor* ]] && cursor_mark="✓"
        printf "  %-15s %-10s %-10s\n" "$name" "$claude_mark" "$cursor_mark"
    done
}

# --- Section: Hooks ---
section_hooks() {
    print_section "Hooks"
    printf "  %-25s %-10s %-10s\n" "Event" "Claude" "Cursor"
    printf "  %-25s %-10s %-10s\n" "───────" "──────" "──────"

    # Claude hooks
    local claude_hooks="$SCRIPT_DIR/claude/hooks.json"
    local cursor_hooks="$SCRIPT_DIR/cursor/hooks/hooks.json"

    # Collect all events
    local events=()
    if has_jq && [[ -f "$claude_hooks" ]]; then
        while IFS= read -r evt; do
            events+=("$evt")
        done < <(jq -r '.hooks | keys[]' "$claude_hooks" 2>/dev/null)
    fi
    if has_jq && [[ -f "$cursor_hooks" ]]; then
        while IFS= read -r evt; do
            events+=("$evt")
        done < <(jq -r '.hooks[].event' "$cursor_hooks" 2>/dev/null)
    fi

    # Deduplicate and print
    printf '%s\n' "${events[@]}" | sort -u | while IFS= read -r evt; do
        local cc="—" cur="—"
        if has_jq && [[ -f "$claude_hooks" ]]; then
            jq -e ".hooks[\"$evt\"]" "$claude_hooks" >/dev/null 2>&1 && cc="✓"
        fi
        if has_jq && [[ -f "$cursor_hooks" ]]; then
            jq -e ".hooks[] | select(.event == \"$evt\")" "$cursor_hooks" >/dev/null 2>&1 && cur="✓"
        fi
        printf "  %-25s %-10s %-10s\n" "$evt" "$cc" "$cur"
    done
}

# --- Section: Skills ---
section_skills() {
    print_section "Skills"
    printf "  %-25s %-10s %-10s\n" "Skill" "Claude" "Cursor"
    printf "  %-25s %-10s %-10s\n" "───────" "──────" "──────"

    # Collect skill names from both tools
    local skills=()
    for skill_dir in "$SCRIPT_DIR"/claude/skills/*/; do
        [[ -d "$skill_dir" ]] || continue
        skills+=("$(basename "$skill_dir")")
    done
    for skill_dir in "$SCRIPT_DIR"/cursor/skills/*/; do
        [[ -d "$skill_dir" ]] || continue
        local name
        name="$(basename "$skill_dir")"
        # Add only if not already present
        local found=false
        for s in "${skills[@]}"; do [[ "$s" == "$name" ]] && found=true; done
        $found || skills+=("$name")
    done

    for name in "${skills[@]}"; do
        local cc="—" cur="—"
        [[ -d "$SCRIPT_DIR/claude/skills/$name" ]] && cc="✓"
        [[ -d "$SCRIPT_DIR/cursor/skills/$name" ]] && cur="✓"
        printf "  %-25s %-10s %-10s\n" "$name" "$cc" "$cur"
    done
}

# --- Section: Agents ---
section_agents() {
    print_section "Agents"
    printf "  %-25s %-10s %-10s\n" "Agent" "Claude" "Cursor"
    printf "  %-25s %-10s %-10s\n" "───────" "──────" "──────"

    local agents=()
    for agent in "$SCRIPT_DIR"/claude/agents/*.md; do
        [[ -f "$agent" ]] || continue
        agents+=("$(basename "$agent" .md)")
    done
    for agent in "$SCRIPT_DIR"/cursor/agents/*.md; do
        [[ -f "$agent" ]] || continue
        local name
        name="$(basename "$agent" .md)"
        local found=false
        for a in "${agents[@]}"; do [[ "$a" == "$name" ]] && found=true; done
        $found || agents+=("$name")
    done

    for name in "${agents[@]}"; do
        local cc="—" cur="—"
        [[ -f "$SCRIPT_DIR/claude/agents/$name.md" ]] && cc="✓"
        [[ -f "$SCRIPT_DIR/cursor/agents/$name.md" ]] && cur="✓"
        printf "  %-25s %-10s %-10s\n" "$name" "$cc" "$cur"
    done
}

# --- Section: Rules ---
section_rules() {
    print_section "Rules"
    if [[ -f "$SCRIPT_DIR/shared/rules.md" ]]; then
        print_info "Shared rules: agents/shared/rules.md"
        [[ -f "$SCRIPT_DIR/claude/global-claude.md" ]] && print_info "  → Claude: agents/claude/global-claude.md (includes shared)"
        [[ -f "$SCRIPT_DIR/cursor/rules/shared-rules.mdc" ]] && print_info "  → Cursor: agents/cursor/rules/shared-rules.mdc (generated)"
        [[ ! -f "$SCRIPT_DIR/cursor/rules/shared-rules.mdc" ]] && print_warning "  → Cursor: rules not generated (run dotfiles doctor --fix)"
    else
        print_warning "No shared rules found"
    fi
}

# --- Section: Permissions ---
section_permissions() {
    print_section "Permissions"
    if has_jq && [[ -f "$CLAUDE_SETTINGS" ]]; then
        local allow_count deny_count
        allow_count=$(jq '.permissions.allow // [] | length' "$CLAUDE_SETTINGS" 2>/dev/null || echo 0)
        deny_count=$(jq '.permissions.deny // [] | length' "$CLAUDE_SETTINGS" 2>/dev/null || echo 0)
        printf "  Claude Code: %s allow, %s deny\n" "$allow_count" "$deny_count"
    else
        printf "  Claude Code: (no settings found)\n"
    fi
    if has_jq && [[ -f "$SCRIPT_DIR/cursor/cli-config.json" ]]; then
        local allow_count deny_count
        allow_count=$(jq '.permissions.allow // [] | length' "$SCRIPT_DIR/cursor/cli-config.json" 2>/dev/null || echo 0)
        deny_count=$(jq '.permissions.deny // [] | length' "$SCRIPT_DIR/cursor/cli-config.json" 2>/dev/null || echo 0)
        printf "  Cursor CLI:  %s allow, %s deny\n" "$allow_count" "$deny_count"
    else
        printf "  Cursor CLI:  (no config found)\n"
    fi
}

# --- Main ---
printf "\n"
print_section "Agentic Setup Overview"
printf "\n"
section_mcp
section_hooks
section_skills
section_agents
section_rules
section_permissions
printf "\n"
