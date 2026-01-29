#!/bin/bash
# Install Cursor agent skills via npx skills add
# Requires: Node/npx (FNM or system). Run from install.sh or after sourcing print_utils.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="${DOTFILES_DIR:-$( cd "$SCRIPT_DIR/../.." && pwd )}"
if [[ -z "${print_section:-}" ]]; then
    source "$DOTFILES_DIR/macos/print_utils.sh"
fi

# Ensure npx is available (e.g. FNM may not be in PATH when this runs standalone)
if ! command -v npx >/dev/null 2>&1; then
    if command -v fnm >/dev/null 2>&1; then
        eval "$(fnm env)"
    fi
fi

if ! command -v npx >/dev/null 2>&1; then
    print_info "npx not found; skipping agent skills install"
    exit 0
fi

# Skills to install (owner/repo as used by: npx skills add <owner/repo>)
SKILLS=(
    firecrawl/cli
    # Uncomment or add more from editors/cursor/SKILLS.md:
    # wshobson/agents/fastapi-templates
    # wshobson/agents/python-testing-patterns
    # wshobson/agents/python-performance-optimization
    # vercel-labs/agent-skills/vercel-react-best-practices
    # supabase/agent-skills/supabase-postgres-best-practices
    # anthropics/skills/skill-creator
)

print_section "Agent skills"
for spec in "${SKILLS[@]}"; do
    [[ "$spec" =~ ^[[:space:]]*# ]] && continue
    print_action "Adding skill $spec..."
    if npx --yes skills add "$spec" 2>/dev/null; then
        print_success "$spec installed"
    else
        print_info "Skill $spec skipped (may already be installed or unavailable)"
    fi
done
