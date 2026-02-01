# =============================================================================
# Custom ZSH Theme (based on Amuse)
# =============================================================================
# Two-line prompt: user@host → directory (git) time
#                  $

# Colors
CYAN="%F{51}"
PINK="%F{162}"
RED="%F{1}"
YELLOW="%F{226}"
RESET="%{$reset_color%}"
BOLD="%B"

# Components
_USER="%n@%m"
_DIR="%~"
_TIME="%*"

# Main prompt (two lines)
PROMPT='
${BOLD}${CYAN}${_USER}${RESET}${BOLD}${CYAN} → ${PINK}${_DIR}${RESET} $(git_prompt_info)${BOLD}${RED}${_TIME}${RESET}
${YELLOW}\$${RESET} '

# Git prompt (from oh-my-zsh)
ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg[yellow]%}("
ZSH_THEME_GIT_PROMPT_SUFFIX=")%{$reset_color%} "
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[red]%}*"
ZSH_THEME_GIT_PROMPT_CLEAN=""
