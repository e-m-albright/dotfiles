###################################### Personalized Theme ############################################################################

BOLD="%B"
CLEAR_BOLD="%b"
CLEAR_COLOR="%f"
RED="%F{1}"
BLUE="%F{27}"
CYAN="%F{51}"
PURPLE="%F{56}"
PINK="%F{162}"
YELLOW="%F{226}"
# %{$fg[white]%} - more autoload colors notation - whats the full set?
RESET="%{$reset_color%}"
BOLD_CYAN="%{$fg_bold[cyan]%}"

# https://zsh.sourceforge.io/Doc/Release/Prompt-Expansion.html
_PROMPT_USER="%n"
_PROMPT_MACHINE="%m"
_PROMPT_TIME="%*"      # Current time of day in 24-hour format, with seconds.
_PROMPT_DIR="%~"
_PROMPT_SEPA="@"
_PROMPT_SEPD="\$"

function pyenv_prompt_info() {
  if which pyenv &>/dev/null; then
    local pyenv_version="$(pyenv version-name)"
    echo "${ZSH_THEME_PYENV_PROMPT_PREFIX:=(}${pyenv_version:=system}${ZSH_THEME_PYENV_PROMPT_SUFFIX:=)}"
  fi
}

# function pyenv_prompt_info() {
#     local version="$(pyenv version-name)"
#     echo "${version:gs/%/%%}"
# }


# Use Amuse theme's prompt with mercurial info added
PROMPT="\
${BOLD}${CYAN}${_PROMPT_USER}${_PROMPT_SEPA}${_PROMPT_MACHINE}➜ \
${PINK}${_PROMPT_DIR} \
${RESET}$(git_prompt_info) \
⌚ \
${BOLD}${RED}${_PROMPT_TIME}${RESET}
${YELLOW}${_PROMPT_SEPD}${RESET} "

