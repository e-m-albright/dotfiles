# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source shared print functions
source "$DOTFILES_DIR/macos/print_utils.sh"

# Install oh-my-zsh if not already installed
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    print_action "Installing Oh My Zsh..."
    if RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" >/dev/null 2>&1; then
        print_success "Oh My Zsh installed"
    else
        print_warning "Oh My Zsh install failed — continuing anyway"
    fi
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
    git_name=""
    while [[ -z "$git_name" ]]; do
        printf "  Enter your full name: "
        read git_name
    done
    git_email=""
    while [[ -z "$git_email" ]]; do
        printf "  Enter your email: "
        read git_email
    done
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

# -- Go (disabled — install per-project if needed)
# To enable: uncomment go/golangci-lint in macos/brew.sh and uncomment this block
# print_section "Go"
# if ! command -v go >/dev/null 2>&1; then
#     print_action "Installing Go..."
#     brew install go >/dev/null 2>&1
#     print_success "Go installed"
# else
#     print_info "Go already installed ($(go version | awk '{print $3}'))"
# fi
# GO_TOOLS=(
#     "golang.org/x/tools/gopls@latest"
#     "github.com/go-delve/delve/cmd/dlv@latest"
#     "github.com/air-verse/air@latest"
#     "github.com/sqlc-dev/sqlc/cmd/sqlc@latest"
#     "github.com/pressly/goose/v3/cmd/goose@latest"
#     "github.com/a-h/templ/cmd/templ@latest"
#     "honnef.co/go/tools/cmd/staticcheck@latest"
# )
# for tool in "${GO_TOOLS[@]}"; do
#     tool_name=$(basename "${tool%@*}")
#     if ! command -v "$tool_name" >/dev/null 2>&1; then
#         go install "$tool" >/dev/null 2>&1 && print_info "  $tool_name installed" || print_info "  $tool_name skipped"
#     else
#         print_info "  $tool_name already installed"
#     fi
# done
# print_success "Go tools configured"

# -- Node.js / FNM (Fast Node Manager — installed via brew in brew.sh)
print_section "Node.js / FNM"
if ! command -v fnm >/dev/null 2>&1; then
    print_info "FNM not found (should be installed via brew.sh)"
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
    if curl -fsSL https://bun.sh/install | bash >/dev/null 2>&1; then
        print_success "Bun installed"
    else
        print_warning "Bun install failed — install manually: curl -fsSL https://bun.sh/install | bash"
    fi
else
    print_info "Bun already installed"
fi

# -- Python / UV
print_section "Python / UV"
if ! command -v uv >/dev/null 2>&1; then
    print_action "Installing UV..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
        print_success "UV installed"
    else
        print_warning "UV install failed — install manually: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
else
    print_info "UV already installed"
fi

# Only install Python 3.14 if it's not already installed via UV
if ! command -v python3.14 >/dev/null 2>&1; then
    print_action "Installing Python 3.14 via UV..."
    uv python install 3.14 >/dev/null 2>&1
    print_success "Python 3.14 installed"
else
    print_info "Python 3.14 already installed"
fi

# Jupyter / Marimo — install per-project, not globally
# Use: uv add jupyter marimo (in project virtualenv)
# See also: Hex (hex.tech) for hosted notebook collaboration

# Editor configurations
print_header "📝 Editor Configuration"

# Cursor
if command -v cursor >/dev/null 2>&1; then
    print_section "Cursor"
    . "$DOTFILES_DIR/editors/cursor/extensions.sh"
    mkdir -p ~/Library/Application\ Support/Cursor/User
    ln -sf "$DOTFILES_DIR/editors/cursor/settings.json" ~/Library/Application\ Support/Cursor/User/settings.json 2>/dev/null || true
    # Global Cursor CLI config + MCP servers
    mkdir -p ~/.cursor
    ln -sf "$DOTFILES_DIR/editors/cursor/cli-config.json" ~/.cursor/cli-config.json 2>/dev/null || true
    ln -sf "$DOTFILES_DIR/editors/cursor/mcp.json" ~/.cursor/mcp.json 2>/dev/null || true
    
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
chmod +x "$DOTFILES_DIR/prompts/scaffold.sh" 2>/dev/null || true
chmod +x "$DOTFILES_DIR/.agents/generate-permissions.sh" 2>/dev/null || true
# Remove old 'recipe' symlink if it exists (deprecated)
rm -f "$DOTFILES_DIR/bin/recipe" 2>/dev/null || true
print_success "Recipe book configured"
print_info "  Usage: ~/dotfiles/prompts/scaffold.sh <recipe> [app-type] <path>"
print_info "  Example: ~/dotfiles/prompts/scaffold.sh typescript svelte my-app"

# Claude Code (instructions, plugins, voice, permissions)
print_header "🤖 Claude Code"
print_section "Setup"
. "$DOTFILES_DIR/claude/setup.sh"

# Agent Permissions (safe commands for agentic tools)
print_section "Agent Permissions"
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

# ==========================================================================
# Manual Follow-Up Checklist
# ==========================================================================
print_header "📋 Next Steps"
printf "\n"
printf "  ${BOLD}Required:${NC}\n"
print_todo "Run ${PKG_COLOR}claude${NC} to authenticate (plugins auto-configured)"
print_todo "Run ${PKG_COLOR}gh auth login${NC} to authenticate GitHub CLI"
print_todo "Add SSH key to GitHub: ${PKG_COLOR}pbcopy < ~/.ssh/id_ed25519.pub${NC}"
print_todo "Open Rectangle and grant Accessibility permissions"
print_todo "Verify git identity: ${PKG_COLOR}git config user.name && git config user.email${NC}"
printf "\n"
printf "  ${BOLD}Optional:${NC}\n"
print_todo_optional "Edit ${PKG_COLOR}~/.cursor/mcp.json${NC} to add MCP server API keys"
print_todo_optional "Edit ${PKG_COLOR}~/dotfiles/claude/plugins.yaml${NC} to customize Claude Code plugins"
print_todo_optional "Enable Go — uncomment in ${PKG_COLOR}macos/brew.sh${NC} and ${PKG_COLOR}install.sh${NC}"
printf "\n"
printf "  Run ${PKG_COLOR}dotfiles doctor${NC} to verify everything is set up correctly.\n"
printf "\n"
