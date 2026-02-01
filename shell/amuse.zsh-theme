# =============================================================================
# Custom ZSH Theme
# =============================================================================
# Two-line prompt with git branch:
#   user@host → ~/directory (main*) 14:32:05
#   $

# Colors
CYAN="%F{51}"
PINK="%F{162}"
RED="%F{1}"
YELLOW="%F{226}"
GREEN="%F{82}"
RESET="%{$reset_color%}"
BOLD="%B"

# Components
_USER="%n@%m"
_DIR="%~"
_TIME="%*"

# Main prompt
PROMPT='
${BOLD}${CYAN}${_USER}${RESET} → ${BOLD}${PINK}${_DIR}${RESET} $(git_prompt_info)${RED}${_TIME}${RESET}
${YELLOW}\$${RESET} '

# Git branch display
# Shows: (branch) in green, or (branch*) in yellow if dirty
ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg_bold[green]%}("
ZSH_THEME_GIT_PROMPT_SUFFIX=")%{$reset_color%} "
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[yellow]%}*%{$fg_bold[green]%}"
ZSH_THEME_GIT_PROMPT_CLEAN=""
