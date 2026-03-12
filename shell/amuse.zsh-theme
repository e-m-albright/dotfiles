# =============================================================================
# Custom ZSH Theme
# =============================================================================
# Two-line prompt:
#   ~/directory (main*) [venv]              14:32:05
#   $   (yellow on success, red on failure)

# Colors (modern %F{} syntax only)
CYAN="%F{51}"
PINK="%F{162}"
RED="%F{1}"
YELLOW="%F{226}"
GREEN="%F{82}"
DIM="%F{242}"
RESET="%f"
BOLD="%B"
UNBOLD="%b"

# Main prompt
# Line 1: dir + git + optional venv/node + dim timestamp
# Line 2: $ (red if last command failed)
PROMPT='
${BOLD}${PINK}%~${UNBOLD}${RESET} $(git_prompt_info)$(_venv_info)${DIM}%*${RESET}
%(?.${YELLOW}.${RED})\$${RESET} '

# Git branch display
ZSH_THEME_GIT_PROMPT_PREFIX="${BOLD}${GREEN}("
ZSH_THEME_GIT_PROMPT_SUFFIX=")${UNBOLD}${RESET} "
ZSH_THEME_GIT_PROMPT_DIRTY="${YELLOW}*${GREEN}"
ZSH_THEME_GIT_PROMPT_CLEAN=""

# Python virtualenv indicator
_venv_info() {
    [[ -n "$VIRTUAL_ENV" ]] && echo "${DIM}[${VIRTUAL_ENV:t}]${RESET} "
}
