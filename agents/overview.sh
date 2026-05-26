#!/usr/bin/env bash
# Agentic setup overview — reports what's active across Claude, Cursor, Codex,
# Gemini, and Pi. Reads from canonical sources (.ai/, agents/shared/) plus
# deployed locations (~/.claude/, ~/.codex/, …).
#
# Called by: dotfiles agent overview [--snapshot[=PATH]]

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
source "$DOTFILES_DIR/macos/print_utils.sh"

# Sources
SHARED_MCP="$SCRIPT_DIR/shared/mcp-servers.json"
AI_AGENTS="$DOTFILES_DIR/.ai/agents"
AI_SKILLS="$DOTFILES_DIR/.ai/skills"
AI_RULES="$DOTFILES_DIR/.ai/rules/process"

# Deployed locations
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
CLAUDE_AGENTS_DIR="$HOME/.claude/agents"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
CODEX_AGENTS_DIR="$HOME/.codex/agents"
SHARED_SKILLS_DIR="$HOME/.agents/skills"  # used by codex/pi via npx skills

has_jq() { command -v jq >/dev/null 2>&1; }

# --- Section: MCP Servers ---
section_mcp() {
    print_section "MCP Servers"
    has_jq || { print_warning "jq required"; return; }
    [[ -f "$SHARED_MCP" ]] || { print_warning "No shared MCP config found"; return; }

    printf "  %-15s %-8s %-8s %-8s %-8s\n" "Server" "Claude" "Cursor" "Codex" "Gemini"
    printf "  %-15s %-8s %-8s %-8s %-8s\n" "───────" "──────" "──────" "─────" "──────"
    jq -r 'to_entries[] | select(.value | type == "object") | "\(.key) \(.value.targets | join(","))"' "$SHARED_MCP" | \
    while read -r name targets; do
        local cc="—" cu="—" co="—" ge="—"
        [[ "$targets" == *claude* ]] && cc="✓"
        [[ "$targets" == *cursor* ]] && cu="✓"
        [[ "$targets" == *codex*  ]] && co="✓"
        [[ "$targets" == *gemini* ]] && ge="✓"
        printf "  %-15s %-8s %-8s %-8s %-8s\n" "$name" "$cc" "$cu" "$co" "$ge"
    done
}

# --- Section: Hooks ---
section_hooks() {
    print_section "Hooks"
    printf "  %-25s %-10s %-10s %-10s\n" "Event" "Claude" "Cursor" "Codex"
    printf "  %-25s %-10s %-10s %-10s\n" "───────" "──────" "──────" "─────"

    local claude_hooks="$SCRIPT_DIR/claude/hooks.json"
    local cursor_hooks="$SCRIPT_DIR/cursor/hooks/hooks.json"
    local codex_hooks="$SCRIPT_DIR/codex/hooks.json"

    local events=()
    has_jq || return
    [[ -f "$claude_hooks" ]] && while IFS= read -r evt; do events+=("$evt"); done < <(jq -r '.hooks | keys[]' "$claude_hooks" 2>/dev/null)
    [[ -f "$cursor_hooks" ]] && while IFS= read -r evt; do events+=("$evt"); done < <(jq -r '.hooks[].event' "$cursor_hooks" 2>/dev/null)
    [[ -f "$codex_hooks"  ]] && while IFS= read -r evt; do events+=("$evt"); done < <(jq -r '.hooks | keys[]?' "$codex_hooks" 2>/dev/null)

    printf '%s\n' "${events[@]}" | sort -u | while IFS= read -r evt; do
        [[ -z "$evt" ]] && continue
        local cc="—" cu="—" co="—"
        [[ -f "$claude_hooks" ]] && jq -e ".hooks[\"$evt\"]" "$claude_hooks" >/dev/null 2>&1 && cc="✓"
        [[ -f "$cursor_hooks" ]] && jq -e ".hooks[] | select(.event == \"$evt\")" "$cursor_hooks" >/dev/null 2>&1 && cu="✓"
        [[ -f "$codex_hooks"  ]] && jq -e ".hooks[\"$evt\"]" "$codex_hooks" >/dev/null 2>&1 && co="✓"
        printf "  %-25s %-10s %-10s %-10s\n" "$evt" "$cc" "$cu" "$co"
    done
}

# --- Section: Skills (canonical source + per-vendor deploy status) ---
section_skills() {
    print_section "Skills"
    [[ -d "$AI_SKILLS" ]] || { print_warning "No .ai/skills/ directory"; return; }

    local total
    total=$(find "$AI_SKILLS" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
    print_info "Canonical source: .ai/skills/ ($total skills)"

    local claude_deployed=0 shared_deployed=0
    [[ -d "$CLAUDE_SKILLS_DIR" ]] && claude_deployed=$(find "$CLAUDE_SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    [[ -d "$SHARED_SKILLS_DIR" ]] && shared_deployed=$(find "$SHARED_SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')

    printf "  %-30s %s\n" "Claude (~/.claude/skills/)" "$claude_deployed"
    printf "  %-30s %s\n" "Codex/Pi (~/.agents/skills/)" "$shared_deployed"
}

# --- Section: Subagents ---
section_agents() {
    print_section "Subagents"
    [[ -d "$AI_AGENTS" ]] || { print_warning "No .ai/agents/ directory"; return; }

    printf "  %-25s %-10s %-10s %-10s\n" "Agent" "Claude" "Codex" "Pi"
    printf "  %-25s %-10s %-10s %-10s\n" "───────" "──────" "─────" "──"

    for agent in "$AI_AGENTS"/*.md; do
        [[ -f "$agent" ]] || continue
        local name cc co pi_mark
        name="$(basename "$agent" .md)"
        cc="—"; co="—"; pi_mark="—"
        [[ -f "$CLAUDE_AGENTS_DIR/$name.md" ]] && cc="✓"
        [[ -f "$CODEX_AGENTS_DIR/$name.md"  ]] && co="✓"
        [[ -f "$HOME/.pi/agent/agents/$name.md" ]] && pi_mark="✓"
        printf "  %-25s %-10s %-10s %-10s\n" "$name" "$cc" "$co" "$pi_mark"
    done
}

# --- Section: Rules ---
section_rules() {
    print_section "Rules"
    [[ -d "$AI_RULES" ]] || { print_warning "No .ai/rules/process/"; return; }

    local total
    total=$(find "$AI_RULES" -name '*.mdc' -type f | wc -l | tr -d ' ')
    print_info "Canonical source: .ai/rules/process/ ($total rules)"

    local claude_deployed=0 cursor_deployed=0
    [[ -d "$HOME/.claude/rules" ]] && claude_deployed=$(find "$HOME/.claude/rules" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
    [[ -d "$SCRIPT_DIR/cursor/rules" ]] && cursor_deployed=$(find "$SCRIPT_DIR/cursor/rules" -maxdepth 1 -name '*.mdc' -type l | wc -l | tr -d ' ')

    printf "  %-30s %s symlinked\n" "Claude (~/.claude/rules/)" "$claude_deployed"
    printf "  %-30s %s symlinked\n" "Cursor (cursor/rules/)" "$cursor_deployed"
    print_info "Codex/Pi/Gemini: rules baked into AGENTS.md / GEMINI.md by setup.sh"
}

# --- Section: Permissions ---
section_permissions() {
    print_section "Permissions"
    if has_jq && [[ -f "$CLAUDE_SETTINGS" ]]; then
        local a d
        a=$(jq '.permissions.allow // [] | length' "$CLAUDE_SETTINGS" 2>/dev/null || echo 0)
        d=$(jq '.permissions.deny  // [] | length' "$CLAUDE_SETTINGS" 2>/dev/null || echo 0)
        printf "  %-25s %s allow, %s deny\n" "Claude Code (deployed)" "$a" "$d"
    fi
    if has_jq && [[ -f "$SCRIPT_DIR/claude/permissions.json" ]]; then
        local a d
        a=$(jq '.allow | length' "$SCRIPT_DIR/claude/permissions.json")
        d=$(jq '.deny  | length' "$SCRIPT_DIR/claude/permissions.json")
        printf "  %-25s %s allow, %s deny\n" "Claude (dotfiles source)" "$a" "$d"
    fi
    if has_jq && [[ -f "$SCRIPT_DIR/cursor/cli-config.json" ]]; then
        local a d
        a=$(jq '.permissions.allow // [] | length' "$SCRIPT_DIR/cursor/cli-config.json")
        d=$(jq '.permissions.deny  // [] | length' "$SCRIPT_DIR/cursor/cli-config.json")
        printf "  %-25s %s allow, %s deny\n" "Cursor CLI" "$a" "$d"
    fi
    if [[ -f "$SCRIPT_DIR/codex/default.rules" ]]; then
        local n
        n=$(grep -c '^prefix_rule' "$SCRIPT_DIR/codex/default.rules" 2>/dev/null || echo 0)
        printf "  %-25s %s prefix rules\n" "Codex (default.rules)" "$n"
    fi
}

SNAPSHOT=false
SNAPSHOT_PATH=""
for arg in "$@"; do
    case "$arg" in
        --snapshot) SNAPSHOT=true; SNAPSHOT_PATH="$DOTFILES_DIR/.ai/artifacts/agents-snapshot-$(date +%Y-%m-%d).md" ;;
        --snapshot=*) SNAPSHOT=true; SNAPSHOT_PATH="${arg#--snapshot=}" ;;
    esac
done

run_sections() {
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
}

if [[ "$SNAPSHOT" == true ]]; then
    mkdir -p "$(dirname "$SNAPSHOT_PATH")"
    tmp_out="$(mktemp)"
    set +e; run_sections > "$tmp_out"; set -e
    sed $'s/\x1b\\[[0-9;]*[a-zA-Z]//g' < "$tmp_out" > "$SNAPSHOT_PATH"
    rm -f "$tmp_out"
    printf "Snapshot written: %s\n" "${SNAPSHOT_PATH/#$HOME/~}"
else
    run_sections
fi
