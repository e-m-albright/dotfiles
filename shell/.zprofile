#!/bin/bash

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Bash completion - update path for M1 Macs
[[ -r "/opt/homebrew/etc/profile.d/bash_completion.sh" ]] && . "/opt/homebrew/etc/profile.d/bash_completion.sh"

# Bun
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# FNM (Fast Node Manager) - initialized in .zshrc after Oh My Zsh loads
