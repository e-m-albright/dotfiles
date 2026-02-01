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
ln -sfv "$DOTFILES_DIR/shell/amuse.zsh-theme" ~/.oh-my-zsh/custom/themes/amuse.zsh-theme

# Git identity setup (stored in ~/.gitconfig.local, not committed)
if [ ! -f ~/.gitconfig.local ]; then
    print_section "Git Identity"
    print_action "Setting up git identity..."
    printf "  Enter your full name: "
    read git_name
    printf "  Enter your email: "
    read git_email
    cat > ~/.gitconfig.local << EOF
# Local git identity (not committed to dotfiles repo)
[user]
    name = $git_name
    email = $git_email
EOF
    print_success "Git identity configured"
else
    print_info "Git identity already configured in ~/.gitconfig.local"
fi

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
# -- Go
print_section "Go"
if ! command -v go >/dev/null 2>&1; then
    print_action "Installing Go..."
    brew install go >/dev/null 2>&1
    print_success "Go installed"
else
    print_info "Go already installed ($(go version | awk '{print $3}'))"
fi

# Go tools (installed globally)
print_action "Installing Go tools..."
GO_TOOLS=(
    "golang.org/x/tools/gopls@latest"           # LSP server
    "github.com/go-delve/delve/cmd/dlv@latest"  # Debugger
    "github.com/air-verse/air@latest"           # Live reload
    "github.com/sqlc-dev/sqlc/cmd/sqlc@latest"  # SQL codegen
    "github.com/pressly/goose/v3/cmd/goose@latest"  # Migrations
    "github.com/a-h/templ/cmd/templ@latest"     # HTML templates
    "honnef.co/go/tools/cmd/staticcheck@latest" # Static analysis
)
for tool in "${GO_TOOLS[@]}"; do
    tool_name=$(basename "${tool%@*}")
    if ! command -v "$tool_name" >/dev/null 2>&1; then
        go install "$tool" >/dev/null 2>&1 && print_info "  $tool_name installed" || print_info "  $tool_name skipped"
    else
        print_info "  $tool_name already installed"
    fi
done
print_success "Go tools configured"

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
    
    # Install Railway CLI (deployment platform)
    if ! command -v railway >/dev/null 2>&1; then
        print_action "Installing Railway CLI..."
        npm install -g @railway/cli >/dev/null 2>&1 || true
        print_success "Railway CLI installed"
    else
        print_info "Railway CLI already installed"
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
    
    # Install Cursor CLI agent (command-line tool)
    if ! command -v agent >/dev/null 2>&1; then
        print_action "Installing Cursor CLI agent..."
        curl -fsS https://cursor.com/install | bash >/dev/null 2>&1 || true
        print_success "Cursor CLI agent installed"
    else
        print_info "Cursor CLI agent already installed"
    fi

    # Agent skills (npx skills add) — requires Node/npx
    if command -v fnm >/dev/null 2>&1; then
        eval "$(fnm env)"
    fi
    . "$DOTFILES_DIR/editors/cursor/skills.sh"

    print_success "Cursor configured"
fi

# Prompts / Recipe Book
print_header "📚 Prompts & Recipes"
print_section "Recipe Book"
# Make scripts executable
chmod +x "$DOTFILES_DIR/prompts/init.sh" 2>/dev/null || true
chmod +x "$DOTFILES_DIR/prompts/seed.sh" 2>/dev/null || true
chmod +x "$DOTFILES_DIR/.agents/generate-permissions.sh" 2>/dev/null || true
# Remove old 'recipe' symlink if it exists (deprecated)
rm -f "$DOTFILES_DIR/bin/recipe" 2>/dev/null || true
print_success "Recipe book configured"
print_info "  New project:      ~/dotfiles/prompts/init.sh <recipe> <name>"
print_info "  Existing project: ~/dotfiles/prompts/seed.sh <recipe> <path>"

# Agent Permissions (safe commands for agentic tools)
print_section "Agent Permissions"
# Merge safe commands into ~/.claude/settings.json (requires yq + jq)
if command -v yq >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    "$DOTFILES_DIR/.agents/generate-permissions.sh" claude >/dev/null 2>&1 && \
        print_success "Claude Code permissions merged into ~/.claude/settings.json" || \
        print_warning "Failed to merge Claude Code permissions"
else
    print_warning "Skipping Claude Code permissions (requires yq and jq)"
    print_info "  Install with: brew install yq jq"
    print_info "  Then run: ~/dotfiles/.agents/generate-permissions.sh claude"
fi

# Clear cache
. "$DOTFILES_DIR/bin/dotfiles" clean

mkdir -p ~/code

# Final completion message
print_completion "✨ Dotfiles setup complete!"
