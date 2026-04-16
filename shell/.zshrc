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
alias yz='yazi'  # Terminal file manager

# Git (supplements oh-my-zsh git plugin)
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

# Editors
alias cu='cursor'
# cc: Claude Code with permission profiles/modes
# Usage: cc [-w] [-a|-p|-e] [--chrome] [--scout|--dev|--yolo] [claude args...]
#   -w  worktree    -a  auto mode    -p  plan mode    -e  accept edits
#   --chrome  open in Chrome (web app mode)
# Default profile: dev (override with CLAUDE_PROFILE env var)
cc() {
    local profile="${CLAUDE_PROFILE:-dev}"
    local permission_mode=""
    local use_worktree=false
    local use_chrome=false
    local args=()
    for arg in "$@"; do
        case "$arg" in
            -w|--worktree) use_worktree=true ;;
            -a|--auto)     permission_mode="auto" ;;
            -p|--plan)     permission_mode="plan" ;;
            -e|--edit)     permission_mode="acceptEdits" ;;
            --chrome)      use_chrome=true ;;
            --scout)       profile="scout" ;;
            --dev)         profile="dev" ;;
            --yolo)        profile="yolo" ;;
            -wa|-aw)       use_worktree=true; permission_mode="auto" ;;
            -wp|-pw)       use_worktree=true; permission_mode="plan" ;;
            -we|-ew)       use_worktree=true; permission_mode="acceptEdits" ;;
            *)             args+=("$arg") ;;
        esac
    done
    local cmd=(claude --settings "$HOME/.claude/profiles/${profile}.json")
    if [[ "$use_chrome" == true ]]; then
        cmd+=(--chrome)
    fi
    if [[ "$use_worktree" == true ]]; then
        cmd+=(--worktree)
    fi
    if [[ -n "$permission_mode" ]]; then
        cmd+=(--permission-mode "$permission_mode")
    fi
    "${cmd[@]}" "${args[@]}"
}
# ccc: Claude Code in Chrome — shorthand for cc --chrome
# All cc flags work: ccc -wa, ccc -p, ccc --yolo, etc.
ccc() { cc --chrome "$@"; }

# ccr: Claude Code Review
# Usage: ccr              — review current branch changes vs main (uses /review-pr)
#        ccr 2277         — review PR #2277 (uses /code-review)
#        ccr <url>        — review PR at URL (uses /code-review)
ccr() {
    local target="$1"

    if [[ -z "$target" ]]; then
        # Local branch review: use pr-review-toolkit's 6 specialized agents
        # (comments, tests, error handling, types, code quality, simplification)
        claude --settings "$HOME/.claude/profiles/scout.json" -- \
            "Fetch and merge origin/main first, then run /review-pr"
    else
        # PR review: use code-review plugin (5 parallel agents, confidence
        # scoring, posts structured GitHub comment)
        if [[ "$target" =~ ^https?:// ]]; then
            claude --settings "$HOME/.claude/profiles/scout.json" -- \
                "Run /code-review on this PR: ${target}"
        else
            claude --settings "$HOME/.claude/profiles/scout.json" -- \
                "Run /code-review on PR #${target}"
        fi
    fi
}

# cca: Claude Code Address feedback
# Usage: cca              — address feedback on current branch's PR
#        cca 2277         — address feedback on PR #2277
#        cca <url>        — address feedback on PR at URL
#   Flags: -c  reply to review comments after addressing
#          -p  push changes after addressing
cca() {
    local target=""
    local do_comment=false
    local do_push=false
    local args=()

    for arg in "$@"; do
        case "$arg" in
            -c) do_comment=true ;;
            -p) do_push=true ;;
            -cp|-pc) do_comment=true; do_push=true ;;
            *)  args+=("$arg") ;;
        esac
    done

    target="${args[1]:-}"

    local pr_ref
    if [[ -z "$target" ]]; then
        pr_ref="the PR for the current branch (find it with \`gh pr view --json number -q .number\`)"
    elif [[ "$target" =~ ^[0-9]+$ ]]; then
        pr_ref="#${target}"
    else
        pr_ref="$target"
    fi

    local extra_instructions=""
    if [[ "$do_comment" == true ]]; then
        extra_instructions="${extra_instructions}
After addressing each piece of feedback, reply to the corresponding review comment on GitHub using \`gh api\` to confirm what was done."
    fi
    if [[ "$do_push" == true ]]; then
        extra_instructions="${extra_instructions}
After all feedback is addressed, push the changes to the remote branch with \`git push\`."
    fi

    local prompt="You are an expert developer addressing PR review feedback.
1. Fetch all review comments for ${pr_ref} using \`gh pr view ${pr_ref} --comments\` and \`gh api repos/{owner}/{repo}/pulls/{number}/reviews\` and \`gh api repos/{owner}/{repo}/pulls/{number}/comments\`.
2. For each piece of feedback:
   a. Understand the reviewer's concern fully before acting.
   b. Make the requested change if it improves the code. If you disagree, explain why clearly.
   c. Run any relevant tests/lints to verify your change doesn't break anything.
3. Group related feedback into logical commits with clear messages.
${extra_instructions}"

    claude --worktree --settings "$HOME/.claude/profiles/dev.json" -- "$prompt"
}

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

# fzf — fuzzy finder keybindings (Ctrl-T files, Ctrl-R history, Alt-C cd)
# Sourced before zoxide so `zi` (interactive jump) can use fzf as its picker.
if command -v fzf &>/dev/null; then
    source <(fzf --zsh)
fi

# zoxide — smart `cd` with frecency. Replaces oh-my-zsh `z` plugin.
# Defines `z <pattern>` (jump) and `zi` (interactive picker via fzf).
if command -v zoxide &>/dev/null; then
    eval "$(zoxide init zsh)"
fi

# Bun completions
[[ -s "$HOME/.bun/_bun" ]] && source "$HOME/.bun/_bun"

# OrbStack
# shellcheck source=/dev/null
[[ -f ~/.orbstack/shell/init.zsh ]] && source ~/.orbstack/shell/init.zsh

# =============================================================================
# Local overrides (not in dotfiles repo)
# =============================================================================
# shellcheck source=/dev/null
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# bun completions
[ -s "/Users/evan/.bun/_bun" ] && source "/Users/evan/.bun/_bun"
