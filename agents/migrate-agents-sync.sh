#!/usr/bin/env bash
# Migrate an existing project to the cross-harness agent-rules-sync pattern.
#
# Drops scripts/sync-agent-rules.sh + lefthook fragment into a project, adds
# fenced markers to its AGENTS.md, runs the first bake, and cleans up the
# now-dead .claude/rules / .codex/rules / .gemini/rules symlinks that pretend
# to deliver rules but don't (those harnesses load AGENTS.md, not a rules
# directory, at project level).
#
# Idempotent — safe to re-run. Refuses to overwrite an existing script unless
# --force is passed.
#
# Usage:
#   dotfiles migrate-agents-sync [<project-path>] [--force] [--keep-dead-symlinks]
#
# If <project-path> is omitted, uses the current working directory.

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCAFFOLD_DIR="$DOTFILES_DIR/prompts/scaffolds/agent-rules-sync"

# Colours (only if stdout is a terminal)
if [[ -t 1 ]]; then
    BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
    DIM='\033[2m'; NC='\033[0m'
else
    BLUE=''; GREEN=''; YELLOW=''; DIM=''; NC=''
fi

ok()   { printf "  ${GREEN}✓${NC}  %s\n" "$1"; }
skip() { printf "  ${DIM}○  %s${NC}\n" "$1"; }
info() { printf "  ${BLUE}•${NC}  %s\n" "$1"; }
warn() { printf "  ${YELLOW}⚠${NC}  %s\n" "$1"; }

# --- Args ---
PROJECT=""
FORCE=false
KEEP_DEAD=false

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        --keep-dead-symlinks) KEEP_DEAD=true ;;
        --help|-h)
            sed -n '4,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        --*) printf "Unknown flag: %s\n" "$arg" >&2; exit 1 ;;
        *) PROJECT="$arg" ;;
    esac
done

PROJECT="${PROJECT:-$(pwd)}"
PROJECT="$(cd "$PROJECT" && pwd)"

if [[ ! -d "$PROJECT/.git" ]]; then
    printf "error: %s is not a git repository\n" "$PROJECT" >&2
    exit 1
fi

printf "${BLUE}Migrating %s${NC}\n" "$PROJECT"

# --- 1. Deploy the sync script ---
SCRIPT_DEST="$PROJECT/scripts/sync-agent-rules.sh"
mkdir -p "$PROJECT/scripts"
if [[ -f "$SCRIPT_DEST" ]] && [[ "$FORCE" != true ]]; then
    skip "scripts/sync-agent-rules.sh (already exists; --force to overwrite)"
else
    cp "$SCAFFOLD_DIR/scripts/sync-agent-rules.sh" "$SCRIPT_DEST"
    chmod +x "$SCRIPT_DEST"
    ok "deployed scripts/sync-agent-rules.sh"
fi

# --- 2. Deploy the lefthook fragment (only if not already merged in) ---
LEFTHOOK_FRAGMENT="$PROJECT/lefthook.agent-rules.yml"
if [[ -f "$PROJECT/lefthook.yml" ]] && grep -q "agent-rules-synced" "$PROJECT/lefthook.yml" 2>/dev/null; then
    skip "lefthook.yml already has agent-rules-synced hook"
elif [[ -f "$LEFTHOOK_FRAGMENT" ]]; then
    skip "lefthook.agent-rules.yml (fragment exists; merge it into lefthook.yml)"
else
    cp "$SCAFFOLD_DIR/lefthook.agent-rules.yml" "$LEFTHOOK_FRAGMENT"
    ok "deployed lefthook.agent-rules.yml"
    info "merge into lefthook.yml or invoke it from your hook runner"
fi

# --- 3. Ensure AGENTS.md exists + has fenced markers ---
AGENTS_MD="$PROJECT/AGENTS.md"
BEGIN_MARKER='<!-- BEGIN: project rules (auto-generated from .ai/rules/) -->'
END_MARKER='<!-- END: project rules -->'

if [[ ! -f "$AGENTS_MD" ]]; then
    warn "no AGENTS.md found — create it first, then re-run"
    exit 1
fi

if ! grep -qF "$BEGIN_MARKER" "$AGENTS_MD"; then
    {
        printf '\n---\n\n%s\n%s\n' "$BEGIN_MARKER" "$END_MARKER"
    } >> "$AGENTS_MD"
    ok "added fenced markers to AGENTS.md"
else
    skip "AGENTS.md already has fenced markers"
fi

# --- 4. Run the first sync (bakes rules + creates cursor symlinks) ---
if [[ -d "$PROJECT/.ai/rules" ]]; then
    if (cd "$PROJECT" && ./scripts/sync-agent-rules.sh); then
        ok "ran sync-agent-rules.sh"
    else
        warn "sync-agent-rules.sh failed — see output above"
    fi
else
    warn ".ai/rules/ not found — create rules first, then run scripts/sync-agent-rules.sh"
fi

# --- 5. Clean up dead symlinks ---
# .claude/rules, .codex/rules, .gemini/rules are decorative — those harnesses
# load AGENTS.md (or its symlinks) at project level, not a rules directory.
# Same for the directory-level skill symlinks if they only point at .ai/skills.
if [[ "$KEEP_DEAD" != true ]]; then
    for dead in ".claude/rules" ".codex/rules" ".gemini/rules"; do
        path="$PROJECT/$dead"
        if [[ -L "$path" ]]; then
            target="$(readlink "$path")"
            rm "$path"
            ok "removed dead symlink: $dead → $target"
        fi
    done
else
    skip "dead symlink cleanup (--keep-dead-symlinks)"
fi

printf "\n${GREEN}migration complete${NC}\n"
printf "  next: commit the new scripts/sync-agent-rules.sh + lefthook fragment\n"
printf "        and any AGENTS.md changes. Wire the lefthook fragment into\n"
printf "        the project's pre-commit if it isn't already.\n"
