#!/usr/bin/env bash
set -eo pipefail

export DOTFILES_DIR
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/output.sh
source "$DOTFILES_DIR/scripts/lib/output.sh"
# shellcheck source=../config/runtimes.conf
source "$DOTFILES_DIR/config/runtimes.conf"

# shellcheck source=lib/host.sh
source "$DOTFILES_DIR/scripts/lib/host.sh"
PROFILE=""
if (( $# )); then
    if [[ $# -ne 2 || "$1" != "--profile" ]]; then
        print_error "Usage: dotfiles update [--profile personal|work]"
        exit 2
    fi
    PROFILE="$2"
fi
resolve_host_profile "$PROFILE"

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
    fnm install "$NODE_VERSION"
    fnm use --install-if-missing "$NODE_VERSION"
    fnm default "$NODE_VERSION"
    version=$(node --version)
    print_success "Node.js $NODE_VERSION: $version"
fi

# --- Rust (rustup) ---
if [[ "$PROFILE" == "personal" ]] && command -v rustup >/dev/null 2>&1; then
    print_section "Rust (rustup)"
    rustup update
    version=$(rustc --version | awk '{print $2}')
    print_success "Rust: $version"
fi

# uv is Homebrew-owned and was updated with the other formulae above.
if command -v uv >/dev/null 2>&1; then
    version=$(uv --version)
    print_success "UV: $version"
    uv python install --upgrade "$PYTHON_VERSION"
fi

if [[ "$PROFILE" == "personal" ]] && command -v npx >/dev/null 2>&1; then
    PNPM_HOME="$HOME/.npm-global" npx --yes get-pnpm "$PNPM_VERSION"
fi

# Reconcile exact npm and Go pins after runtime updates. A blanket
# `npm update -g` would create drift from packages.toml.
print_section "Declared software"
if ! "$DOTFILES_DIR/bin/dotfiles" brew install --profile "$PROFILE"; then
    print_error "Declared software reconciliation failed"
    exit 1
fi

print_completion "All updates finished"
