#!/usr/bin/env bash
set -eo pipefail

export DOTFILES_DIR
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/output.sh
source "$DOTFILES_DIR/scripts/lib/output.sh"

printf "${BLUE}%b Profiling shell startup...${NC}\n\n" "$ARROW"
# Startup failures are what we are diagnosing; still report their timings.
# Time total startup

total=$( { time zsh -i -c exit 2>&1 || true; } 2>&1 | grep real | awk '{print $2}')
printf "  Total startup time: ${BOLD}%s${NC}\n\n" "$total"

# Time individual sourced files
printf "  ${BLUE}File-by-file timing:${NC}\n"
for f in ~/.zshenv ~/.zprofile ~/.zshrc; do
    if [[ -f "$f" ]]; then

        t=$( { time zsh -c 'source "$1"' profile-shell "$f" 2>/dev/null || true; } 2>&1 | grep real | awk '{print $2}')
        printf "  %-30s %s\n" "$(basename "$f")" "$t"
    fi
done
printf "\n"
printf "  ${YELLOW}Tip:${NC} If startup is slow, check for heavy evals (fnm env, brew shellenv).\n"
