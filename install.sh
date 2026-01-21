# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source shared print functions
source "$DOTFILES_DIR/macos/print_utils.sh"

# Install oh-my-zsh if not already installed
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    print_action "Installing Oh My Zsh..."
    RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" >/dev/null 2>&1
    print_success "Oh My Zsh installed"
fi

# Set zsh as default shell
if [ "$SHELL" != "$(which zsh)" ]; then
    print_action "Setting zsh as default shell..."
    chsh -s $(which zsh) >/dev/null 2>&1
    print_success "Shell changed to zsh"
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

# Languages & Runtimes
print_header "🔧 Languages & Runtimes"
# -- Rust
print_section "Rust"
if ! command -v rustc >/dev/null 2>&1; then
    print_action "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y >/dev/null 2>&1
    print_success "Rust installed"
else
    print_info "rustc already installed"
fi

# -- Node.js / FNM (Fast Node Manager)
print_section "Node.js / FNM"
if ! command -v fnm >/dev/null 2>&1; then
    print_action "Installing FNM..."
    curl -fsSL https://fnm.vercel.app/install | bash >/dev/null 2>&1
    print_success "FNM installed"
else
    print_info "FNM already installed"
fi

# Initialize FNM and install Node.js LTS (idempotent)
if command -v fnm >/dev/null 2>&1; then
    eval "$(fnm env)"
    
    # Check if Node.js LTS is already installed
    if fnm list 2>/dev/null | grep -q "lts-latest"; then
        print_info "Node.js LTS already installed"
    else
        print_action "Installing Node.js LTS..."
        fnm install --lts >/dev/null 2>&1
        fnm use --install-if-missing lts-latest >/dev/null 2>&1
        fnm default lts-latest >/dev/null 2>&1
        print_success "Node.js LTS installed"
    fi
    
    # Ensure LTS is set as default (idempotent)
    fnm use --install-if-missing lts-latest >/dev/null 2>&1
    fnm default lts-latest >/dev/null 2>&1
    
    # Enable corepack for pnpm/yarn (idempotent - safe to run multiple times)
    if command -v corepack >/dev/null 2>&1; then
        corepack enable >/dev/null 2>&1 || true
        print_info "Corepack enabled (pnpm/yarn support)"
    fi
fi

# -- Bun (Preferred JavaScript package manager / runtime)
print_section "Bun"
if ! command -v bun >/dev/null 2>&1; then
    print_action "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash >/dev/null 2>&1
    print_success "Bun installed"
else
    print_info "Bun already installed"
fi

# -- Python / UV
print_section "Python / UV"
if ! command -v uv >/dev/null 2>&1; then
    print_action "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    print_success "UV installed"
else
    print_info "UV already installed"
fi

# Only install Python 3.12 if it's not already installed via UV
if ! command -v python3.12 >/dev/null 2>&1; then
    print_action "Installing Python 3.12 via UV..."
    uv python install 3.12 >/dev/null 2>&1
    print_success "Python 3.12 installed"
else
    print_info "Python 3.12 already installed"
fi

# Install Marimo (Python notebook alternative)
print_section "Marimo"
if command -v uv >/dev/null 2>&1; then
    # Try to install Marimo via uv
    if ! uv pip list 2>/dev/null | grep -q "^marimo "; then
        print_action "Installing Marimo..."
        if uv pip install marimo >/dev/null 2>&1; then
            print_success "Marimo installed"
        else
            print_info "Marimo installation skipped (will install manually)"
        fi
    else
        print_info "Marimo already installed"
    fi
elif command -v pip3 >/dev/null 2>&1; then
    if ! pip3 list 2>/dev/null | grep -q "^marimo "; then
        print_action "Installing Marimo..."
        if pip3 install --user marimo >/dev/null 2>&1; then
            print_success "Marimo installed"
        else
            print_info "Marimo installation skipped (will install manually)"
        fi
    else
        print_info "Marimo already installed"
    fi
fi

# Install Jupyter (for compatibility with traditional notebooks)
print_section "Jupyter"
if command -v uv >/dev/null 2>&1; then
    if ! uv tool list 2>/dev/null | grep -q "^jupyter "; then
        print_action "Installing Jupyter..."
        if uv tool install jupyter >/dev/null 2>&1; then
            print_success "Jupyter installed"
        else
            print_info "Jupyter installation skipped (will install manually)"
        fi
    else
        print_info "Jupyter already installed"
    fi
fi

# Editor configurations (VS Code & Cursor)
print_header "📝 Editor Configuration"
# VS Code
if command -v code >/dev/null 2>&1; then
    print_section "VS Code"
    . "$DOTFILES_DIR/editors/vscode/extensions.sh"
    mkdir -p ~/Library/Application\ Support/Code/User
    ln -sf "$DOTFILES_DIR/editors/vscode/settings.json" ~/Library/Application\ Support/Code/User/settings.json 2>/dev/null || true
    print_success "VS Code configured"
fi

# Cursor
if command -v cursor >/dev/null 2>&1; then
    print_section "Cursor"
    . "$DOTFILES_DIR/editors/cursor/extensions.sh"
    mkdir -p ~/Library/Application\ Support/Cursor/User
    ln -sf "$DOTFILES_DIR/editors/cursor/settings.json" ~/Library/Application\ Support/Cursor/User/settings.json 2>/dev/null || true
    # Global Cursor CLI config
    mkdir -p ~/.cursor
    ln -sf "$DOTFILES_DIR/editors/cursor/cli-config.json" ~/.cursor/cli-config.json 2>/dev/null || true
    print_success "Cursor configured"
fi

# Clear cache
. "$DOTFILES_DIR/bin/dotfiles" clean

mkdir -p ~/code

# Final completion message
print_completion "✨ Dotfiles setup complete!"
