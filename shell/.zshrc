# =============================================================================
# ZSH Configuration
# =============================================================================
# Optimized for speed and productivity. Loads Oh My Zsh with minimal plugins.

# =============================================================================
# History
# =============================================================================
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt APPEND_HISTORY
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_SAVE_NO_DUPS
setopt HIST_REDUCE_BLANKS
setopt INC_APPEND_HISTORY
setopt EXTENDED_HISTORY
setopt SHARE_HISTORY

# =============================================================================
# Shell Options
# =============================================================================
setopt AUTO_CD
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt NO_CASE_GLOB
setopt NUMERIC_GLOB_SORT
setopt NO_BEEP
setopt COMPLETE_IN_WORD

# =============================================================================
# Path (Homebrew first)
# =============================================================================
export PATH="/opt/homebrew/bin:$PATH"

# =============================================================================
# Oh My Zsh
# =============================================================================
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="amuse"

# Auto-update settings
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 14

# Plugins (minimal for fast startup)
plugins=(
    git         # Git aliases and completions
    z           # Jump to frequent directories
)

source $ZSH/oh-my-zsh.sh

# =============================================================================
# Environment
# =============================================================================
export EDITOR='cursor --wait'
export VISUAL='cursor --wait'
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_NO_ANALYTICS=1

# =============================================================================
# Aliases
# =============================================================================
# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias co='cd ~/code'

# Files
alias ll='ls -lh'
alias la='ls -lAh'
alias l='ls -CF'

# Git (supplements oh-my-zsh git plugin)
alias gs='git status -sb'
alias gd='git diff'
alias gds='git diff --staged'
alias gpl='git pull'
alias gps='git push'
alias gcm='git commit -m'

# Development
alias py='python3'
alias j='just'

# Editors
alias c='cursor'
alias v='code'

# System
alias path='echo $PATH | tr ":" "\n"'
alias reload='source ~/.zshrc'

# =============================================================================
# Functions
# =============================================================================
# Create directory and cd into it
mkcd() { mkdir -p "$@" && cd "$_"; }

# Extract archives
extract() {
    if [[ ! -f "$1" ]]; then
        echo "'$1' is not a valid file"
        return 1
    fi
    case "$1" in
        *.tar.bz2)   tar xjf "$1"   ;;
        *.tar.gz)    tar xzf "$1"   ;;
        *.tar.xz)    tar xJf "$1"   ;;
        *.bz2)       bunzip2 "$1"   ;;
        *.gz)        gunzip "$1"    ;;
        *.tar)       tar xf "$1"    ;;
        *.tbz2)      tar xjf "$1"   ;;
        *.tgz)       tar xzf "$1"   ;;
        *.zip)       unzip "$1"     ;;
        *.7z)        7z x "$1"      ;;
        *)           echo "'$1' cannot be extracted" ;;
    esac
}

# =============================================================================
# Tool Integrations (lazy-loaded where possible)
# =============================================================================
# FNM (Fast Node Manager)
if command -v fnm &>/dev/null; then
    eval "$(fnm env --use-on-cd --shell zsh)"
fi

# Bun completions
[[ -s "$HOME/.bun/_bun" ]] && source "$HOME/.bun/_bun"

# OrbStack
[[ -f ~/.orbstack/shell/init.zsh ]] && source ~/.orbstack/shell/init.zsh

# =============================================================================
# Local overrides (not in dotfiles repo)
# =============================================================================
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# add Pulumi ESC to the PATH
export PATH=$PATH:$HOME/.pulumi/bin
