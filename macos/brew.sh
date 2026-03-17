#!/bin/bash
set -eo pipefail  # Not using -u: brew env vars and optional arrays may be unset

# Source shared print functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/print_utils.sh"

# -----------------------------------------------------------------------------
# Homebrew bootstrap + curated packages
#
# Philosophy:
# - Fast, reliable defaults
# - "Opinionated but removable"
# - Polarizing apps are opt-in via env toggles
# - Edit this file directly to manage packages (organized by category)
#
# Usage:
#   AI=1 PRODUCTIVITY=1 SOCIAL=1 ./macos/brew.sh
# -----------------------------------------------------------------------------

: "${AI:=1}"
: "${PRODUCTIVITY:=1}"
: "${SOCIAL:=1}"

print_header "🍺 Homebrew Setup"
# Install Homebrew if not already installed
if ! command -v brew >/dev/null 2>&1; then
    print_action "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to path if not already present (idempotent check)
    if ! grep -q 'eval "$(/opt/homebrew/bin/brew shellenv)"' "$HOME/.zprofile" 2>/dev/null; then
        echo >> "$HOME/.zprofile"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        print_success "Added Homebrew to .zprofile"
    fi
    eval "$(/opt/homebrew/bin/brew shellenv)"
    print_success "Homebrew installed"
else
    print_info "Homebrew already installed"
fi

print_action "Updating Homebrew..."
brew update >/dev/null 2>&1
brew upgrade >/dev/null 2>&1
print_success "Homebrew updated"

# =============================================================================
# Installation Functions
# =============================================================================

# Unified install helper. Checks if already present, then installs.
# Usage: _brew_install <name> [formula|cask|auto]
_brew_install() {
    local name="$1"
    local mode="${2:-formula}"
    [[ -z "$name" ]] || [[ "$name" =~ ^[[:space:]]*# ]] && return 0

    # Check if already installed via Homebrew
    if brew list "$name" &>/dev/null 2>&1 || brew list --cask "$name" &>/dev/null 2>&1; then
        print_pkg_installed "$name"
        return 0
    fi

    # Check if binary exists on PATH (tap formulas, manual installs)
    if command -v "$name" >/dev/null 2>&1; then
        print_pkg_installed "$name"
        return 0
    fi

    # For casks, also check /Applications
    if [[ "$mode" == "cask" || "$mode" == "auto" ]]; then
        local app_pattern="${name//-/*}"
        if find /Applications -maxdepth 1 -iname "*${app_pattern}*.app" 2>/dev/null | grep -q .; then
            print_pkg_installed "$name"
            return 0
        fi
    fi

    print_pkg_installing "$name"

    case "$mode" in
        formula)
            if brew install "$name" 2>&1; then
                print_pkg_done "$name"
            else
                print_pkg_fail "$name"
            fi
            ;;
        cask)
            if brew install --cask "$name" 2>&1; then
                print_pkg_done "$name"
            else
                print_pkg_fail "$name"
            fi
            ;;
        auto)
            if brew install "$name" &>/dev/null 2>&1; then
                print_pkg_done "$name"
            elif brew install --cask "$name" &>/dev/null 2>&1; then
                print_pkg_done "$name"
            else
                print_pkg_fail "$name"
            fi
            ;;
    esac
    return 0
}

# Convenience wrappers for batch installs
install_packages() {
    for pkg in "$@"; do _brew_install "$pkg" formula; done
}

install_casks() {
    for pkg in "$@"; do _brew_install "$pkg" cask; done
}

install_any() {
    _brew_install "$1" auto
}

# =============================================================================
# Package Lists (edit here to manage your tools)
# =============================================================================

# CLI Tools (formulae)
core_cli=(
    git                 # Version control
    git-lfs             # Git Large File Storage
    git-delta           # Beautiful git diffs (used by .gitconfig)
    gh                  # GitHub CLI (PRs, issues, actions)
    jq                  # JSON processor
    yq                  # YAML processor (like jq for YAML)
    wget                # Web downloader
    openssl             # TLS/crypto toolkit
    "bash-completion@2" # Bash completion
    micro               # Modern terminal text editor
    # tmux              # Terminal multiplexer (disabled)
)

system_cli=(
    htop                # System monitoring
    iftop               # Network traffic monitoring
    nmap                # Network mapping
    dockutil            # Dock management
    terminal-notifier   # macOS notifications from CLI (used by Claude Code hooks)
)

dev_cli=(
    just                # Command runner (like make, but simpler)
    lefthook            # Git hooks (language-agnostic, parallel execution)
    shellcheck          # Static analysis for shell scripts
    hyperfine           # Command-line benchmarking tool
    atlas               # Database schema migration tool (requires ariga/tap)
    duckdb              # Fast analytical database (SQL for analytics)
    railway             # Railway.app CLI (deploy, logs, manage projects)
    # libpq             # PostgreSQL client library (psql, pg_dump — enable if needed)
    # sentry-cli        # Sentry error tracking (releases, source maps, deploys)
    # datadog-ci        # Datadog CI test visibility & synthetics
)

node_cli=(
    fnm                 # Fast Node Manager (node version switching)
)

go_cli=(
    go                  # Go programming language
    golangci-lint       # Go linter aggregator
)

python_cli=(
    py-spy              # Sampling profiler for Python programs
)

# Applications (casks)
essentials=(
    google-chrome       # Web browser
    # iterm2            # Terminal emulator (disabled)
)

# Editors
ide=(
    cursor                 # Primary: AI-native editor (VS Code compatible)
    # visual-studio-code   # Disabled: using Cursor exclusively
)

productivity=(
    rectangle              # Window management
    # flycut               # Clipboard manager
    # raycast              # Launcher + actions; can replace Rectangle/Flycut
    # warp                 # AI terminal (disabled)
    ghostty                # GPU-accelerated terminal
    caffeine               # Intel-only, requires Rosetta
    flux-app               # Screen color temperature
    granola                # AI notepad for meetings
    obsidian               # Knowledge base & note-taking (Markdown)
)

dev_apps=(
    # docker-desktop    # Consider OrbStack instead (faster, lower resource usage on macOS)
    orbstack            # Docker Desktop alternative (faster, better macOS integration)
    linear-linear       # Project management & issue tracking
    # google-cloud-sdk  # Google Cloud SDK (disabled — install per-project if needed)
)

social_apps=(
    spotify
    slack
    # slack-cli         # Slack platform dev CLI (app development, not chat)
    # zoom  # just use the web client, tired of this causing the "microphone" active indicator.
    # discord
    whatsapp
    # super-productivity
    # signal
)

# AI Tools
ai_cli=(
    claude-code          # Anthropic CLI agent
    claude               # Claude Desktop (macOS app)
    # gemini-cli         # Google Gemini CLI (disabled)
    # ollama             # Local LLM runtime (disabled)
    # huggingface-cli    # Hugging Face CLI (disabled — install per-project if needed)
)

# Infrastructure (disabled by default — enable per-need)
# infra_cli=(
#     awscli              # AWS CLI
#     leapp               # Cloud credentials manager
#     geodesic            # Cloud automation shell (via cloudposse)
#     atmos               # Terraform orchestration (via cloudposse)
#     opentofu            # Open-source Terraform alternative
#     # terraform          # HashiCorp IaC (consider opentofu instead)
#     doppler             # Secrets management
# )

# Formulae (formula-only installs, not casks)
formulae=(
    docker-compose
)

# =============================================================================
# Installation
# =============================================================================

print_header "📦 Installing CLI Tools"

# Add required taps before installing packages
print_action "Adding Homebrew taps..."
brew tap ariga/tap >/dev/null 2>&1 || true
print_success "Taps configured"

print_section "Core CLI"
install_packages "${core_cli[@]}"

print_section "System"
install_packages "${system_cli[@]}"

print_section "Developer Tools"
install_packages "${dev_cli[@]}"

print_section "Node.js"
install_packages "${node_cli[@]}"

print_section "Go"
install_packages "${go_cli[@]}"

print_section "Python"
install_packages "${python_cli[@]}"

# Rust via rustup (official installer; preferred over Homebrew for version management)
print_section "Rust (rustup)"
if command -v rustup >/dev/null 2>&1 || command -v cargo >/dev/null 2>&1; then
    print_info "Rust already installed ($(rustc --version 2>/dev/null || echo 'rustup/cargo present'))"
else
    print_action "Installing Rust via rustup..."
    if curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y; then
        # Source cargo env so rustc/cargo are available in this session
        [[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"
        # Ensure .zprofile has cargo env (rustup adds it, but idempotent guard)
        if ! grep -q '.cargo/env' "$HOME/.zprofile" 2>/dev/null; then
            echo >> "$HOME/.zprofile"
            echo '# Rust (rustup)' >> "$HOME/.zprofile"
            echo '[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"' >> "$HOME/.zprofile"
            print_success "Added Rust to .zprofile"
        fi
        print_success "Rust installed ($(rustc --version 2>/dev/null))"
    else
        print_warn "Failed to install Rust via rustup"
    fi
fi

print_header "🖥️  Installing Applications"
print_section "Essentials"
install_casks "${essentials[@]}"

print_section "IDE"
install_casks "${ide[@]}"

if [[ "$PRODUCTIVITY" == "1" ]]; then
    print_section "Productivity Apps"
    install_casks "${productivity[@]}"
fi

print_section "Development Apps"
install_casks "${dev_apps[@]}"

# Install formula-only packages
if [[ ${#formulae[@]} -gt 0 ]]; then
    print_section "Special Formulae"
    for pkg in "${formulae[@]}"; do
        [[ -z "$pkg" ]] || [[ "$pkg" =~ ^[[:space:]]*# ]] && continue
        install_packages "$pkg"
    done
fi

if [[ "$SOCIAL" == "1" ]]; then
    print_section "Social Apps"
    install_casks "${social_apps[@]}"
fi

if [[ "$AI" == "1" ]]; then
    print_section "AI CLI Tools"
    if [[ ${#ai_cli[@]} -gt 0 ]]; then
        for tool in "${ai_cli[@]}"; do
            [[ -z "$tool" ]] || [[ "$tool" =~ ^[[:space:]]*# ]] && continue
            install_any "$tool"
        done
    fi
fi
