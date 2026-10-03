#!/usr/bin/env bash
set -eo pipefail

export DOTFILES_DIR
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/output.sh
source "$DOTFILES_DIR/scripts/lib/output.sh"

print_header "Updating everything"

# --- macOS ---
print_section "macOS system updates"
if sudo softwareupdate -i -a 2>&1 | tail -1; then
    print_success "macOS up to date"
else
    print_error "macOS update failed"
    exit 1
fi

# --- Homebrew ---
if ! "$DOTFILES_DIR/bin/dotfiles" brew upgrade; then
    print_error "Homebrew update failed"
    exit 1
fi

# --- Node.js (fnm) ---
if command -v fnm >/dev/null 2>&1; then
    print_section "Node.js (fnm)"
    fnm_env=$(fnm env)
    eval "$fnm_env"
    fnm install --lts
    fnm use --install-if-missing lts-latest
    fnm default lts-latest
    version=$(node --version)
    print_success "Node.js LTS: $version"
fi

# --- Rust (rustup) ---
if command -v rustup >/dev/null 2>&1; then
    print_section "Rust (rustup)"
    rustup update
    version=$(rustc --version | awk '{print $2}')
    print_success "Rust: $version"
fi

# uv is Homebrew-owned and was updated with the other formulae above.
if command -v uv >/dev/null 2>&1; then
    version=$(uv --version)
    print_success "UV: $version"
fi

# Reconcile exact npm and Go pins after runtime updates. A blanket
# `npm update -g` would create drift from packages.toml.
print_section "Declared software"
if ! "$DOTFILES_DIR/bin/dotfiles" brew install; then
    print_error "Declared software reconciliation failed"
    exit 1
fi

print_completion "All updates finished"
