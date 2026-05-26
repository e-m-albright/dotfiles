#!/usr/bin/env bash
# Shared helpers for vendor setup scripts (agents/{claude,codex,cursor,gemini,pi}/setup.sh).
#
# Sourcing model — these scripts are sourced by `dotfiles agent-setup`, so they
# share a process. We guard helpers with `agentlib_loaded` to make repeated
# sources cheap. Source like:
#
#   source "$DOTFILES_DIR/agents/shared/lib.sh"
#   agentlib_init "$@"        # parses flags, loads MCP_SKIP, sources print utils
#
# Exports (read-only after agentlib_init): RESET_MCP, MCP_SKIP

[[ -n "${AGENTLIB_LOADED:-}" ]] && return 0
AGENTLIB_LOADED=1

# Resolve dotfiles root from this file's location (works regardless of caller cwd).
AGENTLIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_ROOT="$(cd "$AGENTLIB_DIR/../.." && pwd)"
SHARED_MCP_JSON="$AGENTLIB_DIR/mcp-servers.json"
MCP_SKIP_FILE="$HOME/.config/dotfiles/mcp-skip"

# ---- Output --------------------------------------------------------------

# Source print_utils.sh once. Defines print_success, print_warning, etc.
# Provide no-op fallbacks so setup scripts work even if utils are missing.
if ! source "$DOTFILES_ROOT/macos/print_utils.sh" 2>/dev/null; then
    print_success()  { printf "  ✓ %s\n" "$*"; }
    print_warning()  { printf "  ! %s\n" "$*" >&2; }
    print_info()     { printf "  · %s\n" "$*"; }
    print_skip()     { printf "  ○ %s\n" "$*"; }
    print_step()     { printf "    %s\n" "$*"; }
    print_section()  { printf "\n== %s ==\n" "$*"; }
fi

# ---- Init ----------------------------------------------------------------

# agentlib_init "$@" — parses --reset-mcp / --clean and loads MCP_SKIP from
# both env var and $MCP_SKIP_FILE. Re-running is idempotent.
agentlib_init() {
    RESET_MCP=${RESET_MCP:-false}
    CLEAN_MODE=${CLEAN_MODE:-false}
    for arg in "$@"; do
        case "$arg" in
            --reset-mcp) RESET_MCP=true ;;
            --clean)     CLEAN_MODE=true ;;
        esac
    done

    if [[ -f "$MCP_SKIP_FILE" ]]; then
        local file_skips
        file_skips=$(grep -v '^#' "$MCP_SKIP_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
        MCP_SKIP="${MCP_SKIP:+$MCP_SKIP,}$file_skips"
    fi
    export RESET_MCP CLEAN_MODE MCP_SKIP
}

# ---- Tool guards ---------------------------------------------------------

# require_jq — returns 0 if jq is present, 1 (with warning) otherwise.
require_jq() {
    command -v jq >/dev/null 2>&1 && return 0
    print_warning "jq not found — skipping (brew install jq)"
    return 1
}

# require_cmd <cmd> — generic guard for any binary. Quiet on success.
require_cmd() {
    command -v "$1" >/dev/null 2>&1 && return 0
    print_warning "$1 not found — skipping"
    return 1
}

# ---- MCP filtering -------------------------------------------------------

# mcp_skip_json — emit the current MCP_SKIP env var as a JSON array.
mcp_skip_json() {
    if [[ -n "${MCP_SKIP:-}" ]]; then
        printf '%s' "$MCP_SKIP" | jq -Rc 'split(",")'
    else
        echo '[]'
    fi
}

# mcp_managed_keys <target> — JSON array of server names targeting <target>
# (e.g. "claude", "cursor", "codex", "gemini"). Used for --reset-mcp cleanup.
mcp_managed_keys() {
    local target="$1"
    jq --arg t "$target" '[
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index($t)))
        | .[].key
    ]' "$SHARED_MCP_JSON"
}

# mcp_servers_for <target> — JSON object {name: {server config without .targets}}
# Applies MCP_SKIP. Use this to feed jq merges in vendor setup scripts.
mcp_servers_for() {
    local target="$1"
    local skip
    skip=$(mcp_skip_json)
    jq --arg t "$target" --argjson skip "$skip" '
        to_entries
        | map(select(.value | type == "object"))
        | map(select(.value.targets | index($t)))
        | map(select(.key as $k | $skip | index($k) | not))
        | map({key: .key, value: (.value | del(.targets))})
        | from_entries
    ' "$SHARED_MCP_JSON"
}

# ---- Subagent deployment -------------------------------------------------

# deploy_subagents <dest_dir> — copy .ai/agents/*.md into dest_dir. Quiet if
# source dir missing. Echoes count to stdout via print_success.
deploy_subagents() {
    local dest="$1"
    local src="$DOTFILES_ROOT/.ai/agents"
    [[ -d "$src" ]] || return 0
    mkdir -p "$dest"
    local count=0
    for agent in "$src"/*.md; do
        [[ -f "$agent" ]] || continue
        cp "$agent" "$dest/"
        count=$((count + 1))
    done
    [[ $count -gt 0 ]] && print_success "Deployed $count subagents (${dest/#$HOME/~})"
}

# ---- Skills deployment ---------------------------------------------------

# deploy_skills <vendor> — run `npx skills add` to deploy .ai/skills/* for the
# given vendor (claude-code|codex|cursor). The skills CLI deploys to the right
# vendor home dir transparently.
deploy_skills() {
    local vendor="$1"
    local src="$DOTFILES_ROOT/.ai/skills"
    [[ -d "$src" ]] || return 0
    require_cmd npx || return 0
    local count
    count=$(find "$src" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
    if npx skills add "$src" -s '*' -a "$vendor" -g -y --copy >/dev/null 2>&1; then
        print_success "Deployed $count skills via npx skills ($vendor)"
    else
        print_warning "Failed to deploy skills via npx skills ($vendor)"
    fi
}

# ---- Process-rules symlinking --------------------------------------------

# symlink_process_rules <dest_dir> [suffix]
#   Symlinks every .ai/rules/process/*.mdc into dest_dir. Optional suffix
#   override (e.g. ".md" for Claude Code, which doesn't load .mdc).
#   Idempotent — skips links that already point to the correct source.
symlink_process_rules() {
    local dest="$1"
    local suffix="${2:-.mdc}"
    local src="$DOTFILES_ROOT/.ai/rules/process"
    [[ -d "$src" ]] || { print_warning "No process rules at $src"; return 0; }
    mkdir -p "$dest"

    # Clean up legacy symlinks with the *other* suffix (suffix migration safety)
    local other_suffix
    if [[ "$suffix" == ".md" ]]; then other_suffix=".mdc"; else other_suffix=".md"; fi
    find "$dest" -maxdepth 1 -name "*$other_suffix" -type l -delete 2>/dev/null || true

    local total=0
    for rule in "$src"/*.mdc; do
        [[ -f "$rule" ]] || continue
        local name dest_path
        name="$(basename "$rule" .mdc)$suffix"
        dest_path="$dest/$name"
        if [[ -L "$dest_path" ]] && [[ "$(readlink "$dest_path")" == "$rule" ]]; then
            total=$((total + 1))
            continue
        fi
        ln -sf "$rule" "$dest_path"
        total=$((total + 1))
    done
    print_success "Symlinked $total process rules (${dest/#$HOME/~}/*$suffix → dotfiles)"
}
