#!/bin/bash
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
    chsh -s "$(which zsh)" >/dev/null 2>&1
    print_success "Shell changed to zsh"
fi

# Dotfile symlinks
print_section "Symlinks"
_link() {
    local src="$1" dest="$2"
    local name
    name="$(basename "$dest")"
    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$src" ]]; then
        print_skip "$name"
    else
        ln -sf "$src" "$dest"
        print_step "Linked $name"
    fi
}
_link "$DOTFILES_DIR/git/.gitconfig" ~/.gitconfig
_link "$DOTFILES_DIR/git/.gitignore_global" ~/.gitignore_global
_link "$DOTFILES_DIR/shell/.zprofile" ~/.zprofile
_link "$DOTFILES_DIR/shell/.zshenv" ~/.zshenv
_link "$DOTFILES_DIR/shell/.zshrc" ~/.zshrc
_link "$DOTFILES_DIR/shell/amuse.zsh-theme" ~/.oh-my-zsh/custom/themes/amuse.zsh-theme

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

# -- Go
print_section "Go"
if ! command -v go >/dev/null 2>&1; then
    print_info "Go not found (should be installed via brew.sh)"
else
    print_info "Go already installed ($(go version | awk '{print $3}'))"
fi
GO_TOOLS=(
    "golang.org/x/tools/gopls@latest"
    "github.com/go-delve/delve/cmd/dlv@latest"
    "github.com/air-verse/air@latest"
    "github.com/sqlc-dev/sqlc/cmd/sqlc@latest"
    "github.com/pressly/goose/v3/cmd/goose@latest"
    "github.com/a-h/templ/cmd/templ@latest"
    "honnef.co/go/tools/cmd/staticcheck@latest"
)
if command -v go >/dev/null 2>&1; then
    for tool in "${GO_TOOLS[@]}"; do
        tool_name=$(basename "${tool%@*}")
        if ! command -v "$tool_name" >/dev/null 2>&1; then
            go install "$tool" >/dev/null 2>&1 && print_info "  $tool_name installed" || print_info "  $tool_name skipped"
        else
            print_info "  $tool_name already installed"
        fi
    done
    print_success "Go tools configured"
fi

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

# Terminal configuration
print_header "💻 Terminal Configuration"
print_section "Ghostty"
if command -v ghostty >/dev/null 2>&1 || [[ -d "/Applications/Ghostty.app" ]]; then
    mkdir -p ~/.config/ghostty
    ln -sf "$DOTFILES_DIR/terminal/ghostty.config" ~/.config/ghostty/config 2>/dev/null || true
    print_success "Ghostty configured (notifications enabled)"
else
    print_info "Ghostty not installed — skipping config"
fi

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

# Obsidian
OBSIDIAN_VAULT="$HOME/code/private/notes"
if [[ -d "$OBSIDIAN_VAULT/.obsidian" ]]; then
    print_section "Obsidian"
    OBSIDIAN_CONFIGS=(app appearance core-plugins daily-notes graph templates)
    for cfg in "${OBSIDIAN_CONFIGS[@]}"; do
        local_file="$DOTFILES_DIR/editors/obsidian/${cfg}.json"
        vault_file="$OBSIDIAN_VAULT/.obsidian/${cfg}.json"
        if [[ -L "$vault_file" ]] && [[ "$(readlink "$vault_file")" == "$local_file" ]]; then
            print_skip "${cfg}.json"
        else
            ln -sf "$local_file" "$vault_file"
            print_step "Linked ${cfg}.json"
        fi
    done
    # Community plugins
    chmod +x "$DOTFILES_DIR/editors/obsidian/plugins.sh"
    . "$DOTFILES_DIR/editors/obsidian/plugins.sh" "$OBSIDIAN_VAULT"
    print_success "Obsidian configured"
else
    print_info "Obsidian vault not found at $OBSIDIAN_VAULT — skipping config"
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
print_info "  Usage: dotfiles scaffold <recipe> [app-type] <path>"
print_info "  Example: dotfiles scaffold typescript svelte my-app"

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
print_todo "Run ${CYAN}claude${NC} to authenticate (plugins auto-configured)"
print_todo "Run ${CYAN}gh auth login${NC} to authenticate GitHub CLI"
print_todo "Open Rectangle and grant Accessibility permissions"
print_todo "Verify git identity: ${CYAN}git config user.name && git config user.email${NC}"
printf "\n"
printf "  ${BOLD}Optional:${NC}\n"
print_todo_optional "Edit ${CYAN}~/.cursor/mcp.json${NC} to add MCP server API keys"
print_todo_optional "Edit ${CYAN}~/dotfiles/claude/plugins.yaml${NC} to customize Claude Code plugins"
printf "\n"
printf "  Run ${CYAN}dotfiles doctor${NC} to verify everything is set up correctly.\n"
printf "\n"
