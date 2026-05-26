#!/usr/bin/env bash
# shellcheck disable=SC2059
# Verify each agent vendor (claude, cursor, codex, gemini, pi) has its
# surfaces installed. Reports: skills, subagents, MCP, hooks, global prose,
# permissions/auto-approve rules.
#
# Primary vendors are claude/cursor/codex (ADR-0003). Gemini and Pi are
# narrow re-additions (ADR-0005) — they share .ai/agents, .ai/rules/process,
# and .ai/skills, but with limited surfaces.
#
# Path-level checks for all; CLI confirmation where the vendor exposes it.
#
# Exit 0 always (informational).

set -eo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$HOME/dotfiles}"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

check_path() { # vendor label path
    local v="$1" label="$2" path="$3"
    if [[ ! -e "$path" ]]; then
        printf "  ${RED}✗${NC} %-25s ${DIM}%s${NC}\n" "$label" "$path"
        return
    fi
    if [[ -d "$path" ]]; then
        local n
        n=$(find "$path" -maxdepth 2 -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$n" -gt 0 ]]; then
            printf "  ${GREEN}✓${NC} %-25s ${DIM}%d skills @ %s${NC}\n" "$label" "$n" "$path"
        else
            n=$(ls -A "$path" 2>/dev/null | wc -l | tr -d ' ')
            if [[ "$n" -gt 0 ]]; then
                printf "  ${GREEN}✓${NC} %-25s ${DIM}%d entries @ %s${NC}\n" "$label" "$n" "$path"
            else
                printf "  ${YELLOW}○${NC} %-25s ${DIM}empty: %s${NC}\n" "$label" "$path"
            fi
        fi
    else
        printf "  ${GREEN}✓${NC} %-25s ${DIM}%s${NC}\n" "$label" "$path"
    fi
}

check_cli() { # vendor probe-cmd expected-substring
    local v="$1" cmd="$2" expect="$3"
    local bin="${cmd%% *}"
    if ! command -v "$bin" >/dev/null 2>&1; then
        printf "  ${YELLOW}-${NC} %-25s ${DIM}%s not installed${NC}\n" "CLI report" "$bin"
        return
    fi
    local out count
    out=$(eval "$cmd" 2>&1 || true)
    count=$(printf '%s\n' "$out" | grep -cF "$expect" 2>/dev/null) || count=0
    if [[ "${count:-0}" -gt 0 ]]; then
        printf "  ${GREEN}✓${NC} %-25s ${DIM}%d × '%s' via: %s${NC}\n" "CLI report" "$count" "$expect" "$cmd"
    else
        printf "  ${YELLOW}○${NC} %-25s ${DIM}'%s' not found via: %s${NC}\n" "CLI report" "$expect" "$cmd"
    fi
}

printf "${BLUE}══ Claude Code ══${NC}\n"
check_path claude "skills"        "$HOME/.claude/skills"
check_path claude "subagents"     "$HOME/.claude/agents"
check_path claude "rules"         "$HOME/.claude/rules"
check_path claude "MCP config"    "$HOME/.claude.json"
check_path claude "settings.json" "$HOME/.claude/settings.json"
check_path claude "CLAUDE.md"     "$HOME/.claude/CLAUDE.md"
printf "  ${DIM}CLI confirmation: skills auto-listed in every Claude Code session via Skill tool${NC}\n"

printf "\n${BLUE}══ Cursor ══${NC}\n"
check_path cursor "skills (legacy)"   "$HOME/.cursor/skills"
check_path cursor "skills-cursor"     "$HOME/.cursor/skills-cursor"
check_path cursor "MCP config"        "$HOME/.cursor/mcp.json"
check_path cursor "rules (project)"   "$DOTFILES_DIR/agents/cursor/rules"
printf "  ${DIM}CLI confirmation: GUI only — Cursor → Settings → MCP / Rules${NC}\n"

printf "\n${BLUE}══ Codex ══${NC}\n"
check_path codex "skills (vendor)"  "$HOME/.codex/skills"
check_path codex "skills (shared)"  "$HOME/.agents/skills"
check_path codex "subagents"        "$HOME/.codex/agents"
check_path codex "AGENTS.md"        "$HOME/.codex/AGENTS.md"
check_path codex "config.toml"      "$HOME/.codex/config.toml"
check_path codex "hooks.json"       "$HOME/.codex/hooks.json"
check_path codex "default.rules"    "$HOME/.codex/rules/default.rules"
printf "  ${DIM}CLI confirmation: 'codex' (interactive) — no list-skills subcommand${NC}\n"

printf "\n${BLUE}══ Gemini ══${NC}\n"
if command -v gemini >/dev/null 2>&1; then
    check_path gemini "settings.json"    "$HOME/.gemini/settings.json"
    check_path gemini "GEMINI.md"        "$HOME/.gemini/GEMINI.md"
    printf "  ${DIM}CLI confirmation: 'gemini' (interactive)${NC}\n"
else
    printf "  ${YELLOW}-${NC} %-25s ${DIM}gemini CLI not installed${NC}\n" "skipped"
fi

printf "\n${BLUE}══ Pi ══${NC}\n"
if command -v pi >/dev/null 2>&1; then
    check_path pi "settings.json"       "$HOME/.pi/agent/settings.json"
    check_path pi "models.json"         "$HOME/.pi/agent/models.json"
    check_path pi "AGENTS.md"           "$HOME/.pi/agent/AGENTS.md"
    check_path pi "subagents"           "$HOME/.pi/agent/agents"
    check_path pi "skills (shared)"     "$HOME/.agents/skills"
    printf "  ${DIM}CLI confirmation: 'pi' (interactive, LM Studio local-first)${NC}\n"
else
    printf "  ${YELLOW}-${NC} %-25s ${DIM}pi CLI not installed${NC}\n" "skipped"
fi

printf "\n${DIM}── Summary ──${NC}\n"
printf "Skills deploy via the public ${DIM}npx skills${NC} CLI to claude (~/.claude/skills/) and codex (~/.agents/skills/).\n"
printf "Rules are baked into each vendor's global file (Claude reads ${DIM}~/.claude/rules/*.md${NC} natively).\n"
printf "Verification depth varies — see CLI-confirmation lines above.\n"
printf "To deploy or refresh:  ${DIM}dotfiles agent setup${NC}\n"
