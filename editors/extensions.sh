#!/bin/bash

# Shared extension installer for VS Code and Cursor
# Usage: ./extensions.sh [code|cursor]

EDITOR="${1:-code}"
EDITOR_NAME="VS Code"

if [[ "$EDITOR" == "cursor" ]]; then
    EDITOR_NAME="Cursor"
fi

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'
CHECK="${GREEN}✓${NC}"
BULLET="${CYAN}•${NC}"

# Check if editor is installed
if ! command -v "$EDITOR" >/dev/null 2>&1; then
    printf "${BULLET} %s not found. Skipping extension installation.\n" "$EDITOR_NAME"
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
    if "$EDITOR" --list-extensions 2>/dev/null | grep -q "^${ext_id}$"; then
        ((skipped_count++))
        return 0  # Already installed, skip silently
    fi
    
    # Install the extension
    if "$EDITOR" --install-extension "$ext_id" --force >/dev/null 2>&1; then
        printf "  ${CHECK} ${GREEN}%s${NC}\n" "$ext_name"
        ((installed_count++))
        return 0
    fi
    
    return 1
}

# Universal / Productivity
install_extension "aaron-bond.better-comments"
install_extension "streetsidesoftware.code-spell-checker"
install_extension "gruntfuggly.todo-tree"
install_extension "vscode-icons-team.vscode-icons"
install_extension "usernamehw.errorlens"  # Inline error highlighting (best-in-class DX)
# install_extension "EditorConfig.EditorConfig" # Considering this one

# Version Control
install_extension "eamodio.gitlens"

# Files
install_extension "tamasfe.even-better-toml"

# Docker
install_extension "ms-azuretools.vscode-docker"

# Python (best-in-class DX)
install_extension "ms-python.python"          # Python language support + Pylance
install_extension "ms-python.debugpy"        # Python debugging
install_extension "charliermarsh.ruff"       # Fast Python linter/formatter (replaces flake8/pylint)
install_extension "marimo-team.marimo"       # Marimo notebooks (reactive Python notebooks)

# ML / Data Science
install_extension "ms-toolsai.jupyter"        # Jupyter notebook support
install_extension "ms-toolsai.vscode-tensorboard"  # TensorBoard integration

# TypeScript / SvelteKit (best-in-class DX)
install_extension "svelte.svelte-vscode"     # Svelte/SvelteKit language support
install_extension "biomejs.biome"            # Fast linter/formatter (preferred over ESLint+Prettier)
install_extension "dbaeumer.vscode-eslint"   # ESLint (fallback for legacy projects)
install_extension "esbenp.prettier-vscode"   # Prettier (fallback for legacy projects)
install_extension "ms-playwright.playwright" # E2E testing support

# HTML & CSS / Tailwind
install_extension "bradlc.vscode-tailwindcss"  # Tailwind IntelliSense
install_extension "stivo.tailwind-fold"       # Collapse Tailwind classes
install_extension "formulahendry.auto-rename-tag"  # Auto-rename HTML tags

# Summary (only show if something was installed)
if [[ $installed_count -gt 0 ]]; then
    printf "  ${CHECK} ${GREEN}Installed %d %s extension(s)${NC}\n" "$installed_count" "$EDITOR_NAME"
elif [[ $skipped_count -gt 0 ]]; then
    printf "  ${BULLET} ${CYAN}All %s extensions already installed${NC}\n" "$EDITOR_NAME"
fi
