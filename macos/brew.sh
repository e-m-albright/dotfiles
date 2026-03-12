#!/bin/bash
set -eo pipefail  # Removed 'u' to allow empty arrays

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

# Function to install packages if not already installed
install_packages() {
    local pkgs=("$@")
    [[ ${#pkgs[@]} -eq 0 ]] && return 0
    for pkg in "${pkgs[@]}"; do
        [[ -z "$pkg" ]] || [[ "$pkg" =~ ^[[:space:]]*# ]] && continue
        # Check brew list first (authoritative for Homebrew-managed packages)
        if brew list "$pkg" &>/dev/null 2>&1; then
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (Homebrew)${NC}\n" "$pkg"
            continue
        fi
        # Fallback: check if binary exists (works for tap formulas, manual installs)
        if command -v "$pkg" >/dev/null 2>&1; then
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed${NC}\n" "$pkg"
            continue
        fi
        printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$pkg"
        if brew install "$pkg" 2>&1; then
            printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$pkg"
        else
            printf "  ${WARN} ${YELLOW}Failed to install ${PKG_COLOR}%s${NC} ${YELLOW}(may not be available via Homebrew)${NC}\n" "$pkg"
        fi
    done
}

# Function to install cask packages if not already installed
install_casks() {
    local casks=("$@")
    [[ ${#casks[@]} -eq 0 ]] && return 0
    for cask in "${casks[@]}"; do
        [[ -z "$cask" ]] || [[ "$cask" =~ ^[[:space:]]*# ]] && continue
        
        # Check if installed via Homebrew
        if brew list --cask "$cask" &>/dev/null 2>&1; then
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (Homebrew)${NC}\n" "$cask"
            continue
        fi
        
        # Check if app exists in /Applications (case-insensitive, common patterns)
        # Convert cask name to app name: granola -> Granola.app, google-chrome -> Google Chrome.app
        local app_pattern="${cask//-/*}"  # granola -> granola, google-chrome -> google*chrome
        if find /Applications -maxdepth 1 -iname "*${app_pattern}*.app" 2>/dev/null | grep -q .; then
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (manual)${NC}\n" "$cask"
            continue
        fi
        
        # Try to install via Homebrew
        printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$cask"
        if brew install --cask "$cask" 2>&1; then
            printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$cask"
        else
            printf "  ${WARN} ${YELLOW}Failed to install ${PKG_COLOR}%s${NC} ${YELLOW}(may not be available via Homebrew)${NC}\n" "$cask"
        fi
    done
}

install_any() {
    # Prefer formula; fall back to cask.
    local name="$1"
    [[ -z "$name" ]] || [[ "$name" =~ ^[[:space:]]*# ]] && return 0
    
    # Check brew list first (authoritative source, shows Homebrew origin)
    if brew list "$name" &>/dev/null 2>&1; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (Homebrew formula)${NC}\n" "$name"
        return 0
    fi
    if brew list --cask "$name" &>/dev/null 2>&1; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (Homebrew cask)${NC}\n" "$name"
        return 0
    fi

    # Fallback: check if binary exists (manual installs, tap formulas)
    local bin_name="${name//-/_}"
    local bin_name2="${name//-/}"
    if command -v "$name" >/dev/null 2>&1 || \
       command -v "$bin_name" >/dev/null 2>&1 || \
       command -v "$bin_name2" >/dev/null 2>&1; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed${NC}\n" "$name"
        return 0
    fi

    printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$name"
    if brew install "$name" &>/dev/null 2>&1; then
        printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed (formula)${NC}\n" "$name"
        return 0
    fi
    if brew install --cask "$name" &>/dev/null 2>&1; then
        printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed (cask)${NC}\n" "$name"
        return 0
    fi

    printf "  ${WARN} ${YELLOW}Skipped ${PKG_COLOR}%s${NC} ${YELLOW}(not available via Homebrew)${NC}\n" "$name"
    return 0
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
    # libpq             # PostgreSQL client library (psql, pg_dump — enable if needed)
)

terminal_cli=(
    # tmux              # Terminal multiplexer (disabled)
    "bash-completion@2" # Bash completion
)

network_cli=(
    nmap                # Network mapping
)

dev_cli=(
    openssl             # Security tools
    htop                # System monitoring
    iftop               # Network traffic monitoring
    just                # Command runner (like make, but simpler)
    duckdb              # Fast analytical database (SQL for analytics)
    hyperfine           # Command-line benchmarking tool
    py-spy              # Sampling profiler for Python programs
    # go                # Go programming language (disabled — install per-project if needed)
    # golangci-lint     # Go linter aggregator (disabled — install with Go if needed)
    atlas               # Database schema migration tool (requires ariga/tap)
    lefthook            # Git hooks (language-agnostic, parallel execution)
    fnm                 # Fast Node Manager (node version switching)
)

mac_cli=(
    dockutil            # Dock management
)

# Applications (casks)
essentials=(
    google-chrome       # Web browser
    # iterm2            # Terminal emulator (disabled)
)

# Editors
ide=(
    cursor                 # Primary: AI-native editor (VS Code compatible)
    visual-studio-code     # Fallback: when Cursor isn't suitable
)

productivity=(
    rectangle              # Window management
    # flycut               # Clipboard manager
    # raycast              # Launcher + actions; can replace Rectangle/Flycut
    # warp                 # AI terminal (disabled)
    ghostty                # GPU-accelerated terminal
    caffeine               # Intel-only, requires Rosetta
    flux-app               # Screen color temperature
    # granola              # AI notepad for meetings (disabled)
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
    # zoom  # just use the web client, tired of this causing the "microphone" active indicator.
    # discord
    # whatsapp
    # super-productivity
    # signal
)

# AI Tools
ai_cli=(
    claude-code          # Anthropic CLI agent
    claude               # Claude Desktop (macOS app)
    # gemini-cli         # Google Gemini CLI (disabled)
    # ollama             # Local LLM runtime (disabled — install per-project if needed)
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

print_section "Terminal CLI"
install_packages "${terminal_cli[@]}"

print_section "Developer CLI"
install_packages "${dev_cli[@]}"

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

print_section "Network CLI"
install_packages "${network_cli[@]}"

print_section "macOS CLI"
install_packages "${mac_cli[@]}"

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
