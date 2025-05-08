#!/bin/bash
set -euo pipefail

# Install Homebrew if not already installed
if ! command -v brew >/dev/null 2>&1; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to path if not already present
    if ! grep -q 'eval "$(/opt/homebrew/bin/brew shellenv)"' /Users/$USER/.zprofile; then
        echo >> /Users/$USER/.zprofile
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/$USER/.zprofile
    fi
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo "✓ Homebrew installed"
fi

echo "Updating Homebrew..."
brew update
brew upgrade
echo "✓ Homebrew updated"

# Install CLI packages
echo "Installing CLI tools..."

qol_utils=(
    tmux
    dockutil
    "bash-completion@2"
)

git_tools=(
    git
    git-lfs
)

dev_utils=(
    htop
    iftop
    openssl
    wget
    jq
    nmap
)

# Function to install packages if not already installed
install_packages() {
    local pkgs=("$@")
    for pkg in "${pkgs[@]}"; do
        if ! brew list "$pkg" &>/dev/null; then
            echo "Installing $pkg..."
            brew install "$pkg"
            echo "✓ $pkg installed"
        else
            echo "• $pkg already installed"
        fi
    done
}

# Install packages by category
echo "Installing QOL utilities..."
install_packages "${qol_utils[@]}"

echo "Installing Git tools..."
install_packages "${git_tools[@]}"

echo "Installing dev utilities..."
install_packages "${dev_utils[@]}"

echo "✓ All CLI tools installed"

# Install cask packages
echo "Installing applications..."

# Define cask packages in arrays
apps=(
    google-chrome
    spotify
    discord
    whatsapp
    zoom
    signal
    super-productivity
)

qol_apps=(
    rectangle
    caffeine
    flux
    flycut
)

dev_apps=(
    visual-studio-code
    cursor
    iterm2
    docker
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

# Function to install cask packages if not already installed
install_casks() {
    local casks=("$@")
    for cask in "${casks[@]}"; do
        if ! brew list --cask "$cask" &>/dev/null; then
            echo "Installing $cask..."
            brew install --cask "$cask"
            echo "✓ $cask installed"
        else
            echo "• $cask already installed"
        fi
    done
}

# Install cask packages by category
echo "Installing general applications..."
install_casks "${apps[@]}"

echo "Installing QOL applications..."
install_casks "${qol_apps[@]}"

echo "Installing development tools..."
install_casks "${dev_apps[@]}"

# Install Docker Compose separately as it's not a cask
if ! brew list docker-compose &>/dev/null; then
    echo "Installing docker-compose..."
    brew install docker-compose
    echo "✓ docker-compose installed"
else
    echo "• docker-compose already installed"
fi

echo "Installing Quick Look plugins..."
install_casks "${quicklook_plugins[@]}"

# Optional installations (commented out by default)
# install_casks postman insomnia figma

echo "✓ All applications successfully installed!"