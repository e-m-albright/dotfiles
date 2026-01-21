#!/bin/bash
set -eo pipefail  # Removed 'u' to allow empty arrays

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Symbols
CHECK="${GREEN}✓${NC}"
BULLET="${CYAN}•${NC}"
WARN="${YELLOW}⚠${NC}"
ARROW="${BLUE}→${NC}"

# Package name color (subtle teal/blue)
PKG_COLOR='\033[0;36m'  # Cyan/teal

# Print functions (using printf for better compatibility)
print_header() {
    printf "\n"
    printf "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${BOLD}${BLUE}  %s${NC}\n" "$1"
    printf "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "\n"
}

print_section() {
    printf "\n"
    printf "${CYAN}┌─${NC} ${BOLD}${CYAN}%s${NC}\n" "$1"
}

print_success() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${CHECK} ${GREEN}${PKG_COLOR}%s${NC}${GREEN} %s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${CHECK} ${GREEN}%s${NC}\n" "$msg"
    fi
}

print_info() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}%s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${BULLET} ${CYAN}%s${NC}\n" "$msg"
    fi
}

print_warn() {
    printf "  ${WARN} ${YELLOW}%s${NC}\n" "$1"
}

print_action() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${ARROW} ${BOLD}${PKG_COLOR}%s${NC}${BOLD} %s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${ARROW} ${BOLD}%s${NC}\n" "$msg"
    fi
}

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
            brew install "$pkg" >/dev/null 2>&1
            printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$pkg"
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
        if ! brew list --cask "$cask" &>/dev/null; then
            printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$cask"
            brew install --cask "$cask" >/dev/null 2>&1
            printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$cask"
        else
            printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed${NC}\n" "$cask"
        fi
    done
}

install_any() {
    # Prefer formula; fall back to cask.
    local name="$1"
    [[ -z "$name" ]] || [[ "$name" =~ ^[[:space:]]*# ]] && return 0
    
    if brew list "$name" &>/dev/null; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (formula)${NC}\n" "$name"
        return 0
    fi
    if brew list --cask "$name" &>/dev/null; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}already installed (cask)${NC}\n" "$name"
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
)

dev_apps=(
    docker-desktop
    google-cloud-sdk
)

social_apps=(
    spotify
    zoom
    discord
    # whatsapp
    # super-productivity
    # signal
)

# AI Tools
ai_cli=(
    claude-code          # Anthropic CLI
    gemini-cli           # Google Gemini CLI
    ollama               # Local LLM runtime
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

printf "\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${CHECK} ${BOLD}${GREEN}All CLI tools installed${NC}\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "\n"

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

printf "\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${CHECK} ${BOLD}${GREEN}All applications successfully installed!${NC}\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "\n"
