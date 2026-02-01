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
        if ! brew list "$pkg" &>/dev/null; then
            printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$pkg"
            if brew install "$pkg" 2>&1; then
                printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$pkg"
            else
                printf "  ${WARN} ${YELLOW}Failed to install ${PKG_COLOR}%s${NC} ${YELLOW}(may not be available via Homebrew)${NC}\n" "$pkg"
            fi
        else
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed${NC}\n" "$pkg"
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
    # Optimized: Check binary first (fast), then brew list (slower but necessary)
    local name="$1"
    [[ -z "$name" ]] || [[ "$name" =~ ^[[:space:]]*# ]] && return 0
    
    # Fast check: if binary exists, it's installed (works for most CLI tools)
    # Try common binary name variations (much faster than brew list)
    local bin_name="${name//-/_}"  # claude-code -> claude_code
    local bin_name2="${name//-/}"  # claude-code -> claudecode
    if command -v "$name" >/dev/null 2>&1 || \
       command -v "$bin_name" >/dev/null 2>&1 || \
       command -v "$bin_name2" >/dev/null 2>&1; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed${NC}\n" "$name"
        return 0
    fi
    
    # Slower check: use brew list (only if binary check failed)
    # Combine both checks with || to short-circuit (faster than separate if statements)
    if brew list "$name" &>/dev/null 2>&1 || brew list --cask "$name" &>/dev/null 2>&1; then
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
    jq                  # JSON processor
    wget                # Web downloader
)

terminal_cli=(
    tmux                # Terminal multiplexer
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
)

mac_cli=(
    dockutil            # Dock management
)

# Applications (casks)
essentials=(
    google-chrome       # Web browser
    # iterm2            # Terminal emulator (using Warp instead)
)

# IDEs (casks) — pick exactly one as your daily driver.
# Switch by commenting/uncommenting inline.
ide=(
    # visual-studio-code   # VS Code
    cursor                 # AI-native editor
    # zed                  # Ultra-fast editor
)

productivity=(
    # rectangle            # Window management
    # flycut               # Clipboard manager
    raycast                # Launcher + actions; can replace Rectangle/Flycut
    warp                   # AI terminal (modern UX)
    caffeine               # Intel-only, requires Rosetta
    flux-app               # Screen color temperature
    granola                # AI notepad for meetings (auto-transcribes, enhances notes)
)

dev_apps=(
    # docker-desktop    # Consider OrbStack instead (faster, lower resource usage on macOS)
    orbstack            # Docker Desktop alternative (faster, better macOS integration)
    linear-linear       # Project management & issue tracking
    google-cloud-sdk
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
    claude-code          # Anthropic CLI
    gemini-cli           # Google Gemini CLI
    ollama               # Local LLM runtime
    huggingface-cli      # Hugging Face CLI (model management, downloads)
    # antigravity          # Distribution TBD
)

quicklook_plugins=(
    qlcolorcode
    qlstephen
    qlmarkdown
    quicklook-json
    qlprettypatch
    quicklook-csv
    webpquicklook
    qlvideo
)

# Formulae (formula-only installs, not casks)
formulae=(
    docker-compose
)

# =============================================================================
# Installation
# =============================================================================

print_header "📦 Installing CLI Tools"
print_section "Core CLI"
install_packages "${core_cli[@]}"

print_section "Terminal CLI"
install_packages "${terminal_cli[@]}"

print_section "Developer CLI"
install_packages "${dev_cli[@]}"

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

print_section "Quick Look Plugins"
install_casks "${quicklook_plugins[@]}"
