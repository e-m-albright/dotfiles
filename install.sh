# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for final message
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

# Install oh-my-zsh if not already installed
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Installing Oh My Zsh..."
    RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    echo "✓ Oh My Zsh installed"
fi

# Set zsh as default shell
if [ "$SHELL" != "$(which zsh)" ]; then
    echo "Setting zsh as default shell..."
    chsh -s $(which zsh)
    echo "✓ Shell changed to zsh"
fi

# Dotfile symlinks
ln -sfv "$DOTFILES_DIR/git/.gitconfig" ~
ln -sfv "$DOTFILES_DIR/git/.gitignore_global" ~
ln -sfv "$DOTFILES_DIR/shell/.zprofile" ~
ln -sfv "$DOTFILES_DIR/shell/.zshenv" ~
ln -sfv "$DOTFILES_DIR/shell/.zshrc" ~
ln -fv "$DOTFILES_DIR/shell/amuse.zsh-theme" ~/.oh-my-zsh/custom/themes/amuse.zsh-theme

################################################################################
# Set up SSH for Git + Homebrew
. "$DOTFILES_DIR/macos/ssh.sh"
# Install brew with packages & casks
. "$DOTFILES_DIR/macos/brew.sh"
# Setup macos dock
. "$DOTFILES_DIR/macos/dock.sh"
################################################################################

# Languages
# -- Rust
if ! command -v rustc >/dev/null 2>&1; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    echo "✓ Rust installed"
fi

# -- Node.js / FNM (Fast Node Manager)
if ! command -v fnm >/dev/null 2>&1; then
    echo "Installing FNM..."
    curl -fsSL https://fnm.vercel.app/install | bash
    echo "✓ FNM installed"
fi

# Initialize FNM and install Node.js LTS (idempotent)
if command -v fnm >/dev/null 2>&1; then
    eval "$(fnm env)"
    
    # Check if Node.js LTS is already installed
    if fnm list | grep -q "lts-latest"; then
        echo "• Node.js LTS already installed"
    else
        echo "Installing Node.js LTS..."
        fnm install --lts
        fnm use --install-if-missing lts-latest
        fnm default lts-latest
        echo "✓ Node.js LTS installed"
    fi
    
    # Ensure LTS is set as default (idempotent)
    fnm use --install-if-missing lts-latest >/dev/null 2>&1
    fnm default lts-latest >/dev/null 2>&1
    
    # Enable corepack for pnpm/yarn (idempotent - safe to run multiple times)
    if command -v corepack >/dev/null 2>&1; then
        corepack enable >/dev/null 2>&1 || true
        echo "• Corepack enabled (pnpm/yarn support)"
    fi
fi

# -- Bun (Preferred JavaScript package manager / runtime)
if ! command -v bun >/dev/null 2>&1; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
    echo "✓ Bun installed"
fi

# -- Python / UV
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✓ UV installed"
fi

# Only install Python 3.12 if it's not already installed via UV
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Installing Python 3.12 via UV..."
    uv python install 3.12
    echo "✓ Python 3.12 installed"
fi

# Install Marimo (Python notebook alternative)
if command -v uv >/dev/null 2>&1; then
    # Try to install Marimo via uv
    if ! uv pip list 2>/dev/null | grep -q "^marimo "; then
        echo "Installing Marimo..."
        uv pip install marimo >/dev/null 2>&1 && echo "✓ Marimo installed" || echo "• Marimo installation skipped (will install manually)"
    else
        echo "• Marimo already installed"
    fi
elif command -v pip3 >/dev/null 2>&1; then
    if ! pip3 list 2>/dev/null | grep -q "^marimo "; then
        echo "Installing Marimo..."
        pip3 install --user marimo >/dev/null 2>&1 && echo "✓ Marimo installed" || echo "• Marimo installation skipped (will install manually)"
    else
        echo "• Marimo already installed"
    fi
fi

# Editor configurations (VS Code & Cursor)
# VS Code
if command -v code >/dev/null 2>&1; then
    . "$DOTFILES_DIR/editors/vscode/extensions.sh"
    mkdir -p ~/Library/Application\ Support/Code/User
    ln -sf "$DOTFILES_DIR/editors/vscode/settings.json" ~/Library/Application\ Support/Code/User/settings.json 2>/dev/null || true
fi

# Cursor
if command -v cursor >/dev/null 2>&1; then
    . "$DOTFILES_DIR/editors/cursor/extensions.sh"
    mkdir -p ~/Library/Application\ Support/Cursor/User
    ln -sf "$DOTFILES_DIR/editors/cursor/settings.json" ~/Library/Application\ Support/Cursor/User/settings.json 2>/dev/null || true
    # Global Cursor CLI config
    mkdir -p ~/.cursor
    ln -sf "$DOTFILES_DIR/editors/cursor/cli-config.json" ~/.cursor/cli-config.json 2>/dev/null || true
fi

# Clear cache
. "$DOTFILES_DIR/bin/dotfiles" clean

mkdir -p ~/code

# Final completion message
printf "\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${BOLD}${GREEN}  ✨ Dotfiles setup complete!${NC}\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "\n"
