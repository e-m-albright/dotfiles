#!/bin/bash

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'
CHECK="${GREEN}✓${NC}"
BULLET="${CYAN}•${NC}"

# Check if Cursor is installed
if ! command -v cursor >/dev/null 2>&1; then
    printf "${BULLET} Cursor not found. Skipping extension installation.\n"
    exit 0
fi

installed_count=0
skipped_count=0

# Function to install extension if not already installed
install_extension() {
    local ext_id="$1"
    local ext_name="${ext_id##*.}"
    
    # Skip commented lines
    [[ "$ext_id" =~ ^[[:space:]]*# ]] && return 0
    
    # Check if extension is already installed
    if cursor --list-extensions 2>/dev/null | grep -q "^${ext_id}$"; then
        ((skipped_count++))
        return 0  # Already installed, skip silently
    fi
    
    # Install the extension
    if cursor --install-extension "$ext_id" --force >/dev/null 2>&1; then
        printf "  ${CHECK} ${GREEN}%s${NC}\n" "$ext_name"
        ((installed_count++))
        return 0
    fi
    
    return 1
}

# Universal
install_extension "aaron-bond.better-comments"
install_extension "streetsidesoftware.code-spell-checker"
install_extension "gruntfuggly.todo-tree"
install_extension "vscode-icons-team.vscode-icons"

# Version Control
install_extension "eamodio.gitlens"

# Files
install_extension "tamasfe.even-better-toml"

# Docker
install_extension "ms-azuretools.vscode-docker"

# Python
install_extension "ms-python.python"
install_extension "ms-python.debugpy"
install_extension "charliermarsh.ruff"

# JavaScript
install_extension "dbaeumer.vscode-eslint"
install_extension "esbenp.prettier-vscode"
install_extension "crystal-spider.jsdoc-generator"
install_extension "ms-playwright.playwright"
install_extension "wallabyjs.quokka-vscode"

# JavaScript - Svelte
install_extension "svelte.svelte-vscode"
install_extension "fivethree.vscode-svelte-snippets"
install_extension "pivaszbs.svelte-autoimport"
install_extension "ardenivanov.svelte-intellisense"
install_extension "tauri-apps.tauri-vscode"

# HTML & CSS
install_extension "bradlc.vscode-tailwindcss"
install_extension "stivo.tailwind-fold"
install_extension "formulahendry.auto-rename-tag"

# Rust
install_extension "rust-lang.rust-analyzer"

# Summary (only show if something was installed)
if [[ $installed_count -gt 0 ]]; then
    printf "  ${CHECK} ${GREEN}Installed %d Cursor extension(s)${NC}\n" "$installed_count"
elif [[ $skipped_count -gt 0 ]]; then
    printf "  ${BULLET} ${CYAN}All Cursor extensions already installed${NC}\n"
fi
