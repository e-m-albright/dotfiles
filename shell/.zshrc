# shellcheck shell=bash
# =============================================================================
# ZSH Configuration
# =============================================================================
# Optimized for speed and productivity. Loads Oh My Zsh with minimal plugins.

# =============================================================================
# History
# =============================================================================
HISTFILE=~/.zsh_history
HISTSIZE=100000
# shellcheck disable=SC2034 # used by zsh
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
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

# =============================================================================
# Oh My Zsh
# =============================================================================
export ZSH="$HOME/.oh-my-zsh"
# shellcheck disable=SC2034 # used by oh-my-zsh
ZSH_THEME="amuse"

# Auto-update settings
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 14

# Plugins (minimal for fast startup)
# shellcheck disable=SC2034 # used by oh-my-zsh
plugins=(
    git         # Git aliases and completions
    # z         # Replaced by zoxide — see Tool Integrations below
)

# Custom completions (e.g. _dotfiles). Must precede oh-my-zsh, which runs compinit.
fpath=("$HOME/code/public/dotfiles/shell/completions" "${fpath[@]}")

source $ZSH/oh-my-zsh.sh

# =============================================================================
# Environment
# =============================================================================
export EDITOR='zed --wait'
export VISUAL='zed --wait'
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_NO_ANALYTICS=1

# =============================================================================
# Aliases
# =============================================================================
# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Files
alias ll='ls -lh'
alias la='ls -lAh'
alias l='ls -CF'
# yz: yazi wrapper that inherits yazi's final cwd into the shell on exit.
# Without this, quitting yazi leaves you in the dir you launched from.
yz() {
    local tmp
    tmp=$(mktemp -t yazi-cwd.XXXXXX) || return
    yazi "$@" --cwd-file="$tmp"
    local cwd
    IFS= read -r cwd <"$tmp"
    # shellcheck disable=SC2164  # cd is &&-guarded; a failure should not exit the shell
    [[ -n "$cwd" && "$cwd" != "$PWD" ]] && builtin cd -- "$cwd"
    rm -f -- "$tmp"
}

# Git (supplements oh-my-zsh git plugin)
# Drop the plugin's `gpu` (git push upstream) — a footgun next to `gps`, and we
# rarely have an `upstream` remote. `gps`/`gp` cover push.
unalias gpu 2>/dev/null
alias gs='git status -sb'
alias gd='git diff'
alias gds='git diff --staged'
alias gpl='git pull'
alias gps='git push'
alias gcm='git commit -m'

# Development
alias python='python3'
alias pip='pip3'
alias py='python3'
alias j='just'

# Agent launchers (gcmw, gacp, co, cc, ccc, ccr, cca) are workbench-owned;
# `workbench sync` deploys the fragment sourced here.
_wb_launchers="$HOME/.local/share/workbench/shell/agent-launchers.zsh"
[[ -f "$_wb_launchers" ]] && source "$_wb_launchers"
unset _wb_launchers

# System
alias path='echo $PATH | tr ":" "\n"'
alias reload='source ~/.zshrc'

# =============================================================================
# Functions
# =============================================================================
# Create directory and cd into it
mkcd() { mkdir -p "$@" && cd "$_" || return; }

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

# Shared npm global prefix (set via `npm config set prefix ~/.npm-global`) so
# global CLIs survive fnm version switches. Must come after fnm init to win PATH.
export PATH="$HOME/.npm-global/bin:$PATH"

# fzf — fuzzy finder keybindings (Ctrl-T files, Ctrl-R history, Alt-C cd)
# Sourced before zoxide so `zi` (interactive jump) can use fzf as its picker.
if command -v fzf &>/dev/null; then
    # shellcheck disable=SC1090  # process substitution; nothing to statically follow
    source <(fzf --zsh)
fi

# zoxide — smart `cd` with frecency. Replaces oh-my-zsh `z` plugin.
# Defines `z <pattern>` (jump) and `zi` (interactive picker via fzf).
if command -v zoxide &>/dev/null; then
    eval "$(zoxide init zsh)"
fi

# OrbStack
# shellcheck source=/dev/null
[[ -f ~/.orbstack/shell/init.zsh ]] && source ~/.orbstack/shell/init.zsh

# =============================================================================
# Local overrides (not in dotfiles repo)
# =============================================================================
# shellcheck source=/dev/null
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local
