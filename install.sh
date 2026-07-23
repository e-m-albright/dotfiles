#!/bin/bash
set -euo pipefail

# Fail clearly on a non-macOS host instead of cascading through chsh/defaults/
# softwareupdate/duti errors. (This is a macOS bootstrap; the clean-machine CI
# exercises `doctor` on Linux, not install.sh.)
if [[ "$OSTYPE" != darwin* ]]; then
    printf 'install.sh targets macOS (OSTYPE=%s). Aborting.\n' "$OSTYPE" >&2
    exit 1
fi

# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OH_MY_ZSH_COMMIT="677a4592b18c08ddea737f8aca70bac0e9fc9313"
HOMEBREW_INSTALL_COMMIT="fea42d9aedd20a82bea800a6898dcde19401ab1f"
WORKBENCH_COMMIT="dfadab4f9f8f1cccfb2bb5ea4921b2627ef05367"
UV_VERSION="0.11.29"

# Source shared print functions
source "$DOTFILES_DIR/macos/print_utils.sh"

# Install oh-my-zsh if not already installed
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    print_action "Installing Oh My Zsh..."
    if RUNZSH=no sh -c "$(curl -fsSL "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/$OH_MY_ZSH_COMMIT/tools/install.sh")" >/dev/null 2>&1; then
        print_success "Oh My Zsh installed"
    else
        print_warn "Oh My Zsh install failed — continuing anyway"
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
"$DOTFILES_DIR/macos/ssh.sh"

# Homebrew bootstrap — must come before any brew/dotfiles-brew calls
print_section "Homebrew"
if ! command -v brew >/dev/null 2>&1; then
    print_action "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL "https://raw.githubusercontent.com/Homebrew/install/$HOMEBREW_INSTALL_COMMIT/install.sh")"

    # Add Homebrew to PATH for this session and persist for future shells.
    # SC2016: single quotes are intentional — we want the literal string written to .zprofile, not expanded.
    # shellcheck disable=SC2016
    if ! grep -q 'eval "$(/opt/homebrew/bin/brew shellenv)"' "$HOME/.zprofile" 2>/dev/null; then
        # shellcheck disable=SC2016
        printf '\neval "$(/opt/homebrew/bin/brew shellenv)"\n' >> "$HOME/.zprofile"
        print_success "Added Homebrew to .zprofile"
    fi
    eval "$(/opt/homebrew/bin/brew shellenv)"
    print_success "Homebrew installed"
else
    print_info "Homebrew already installed ($(brew --version | head -1))"
fi

# Update Homebrew index so formulae/casks are current.
# (Skipping brew upgrade here — upgrading everything on every setup run is too
# aggressive; packages are managed declaratively via packages.toml instead.)
brew update >/dev/null 2>&1
print_success "Homebrew index updated"

# Ensure uv is present (needed to run the Python CLI for brew install)
print_section "uv (Python package manager)"
if ! command -v uv >/dev/null 2>&1; then
    print_action "Installing uv..."
    if curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | sh >/dev/null 2>&1; then
        # Reload PATH so uv is findable in the same shell session
        export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
        print_success "uv installed"
    else
        print_warn "uv $UV_VERSION install failed"
    fi
else
    print_info "uv already installed ($(uv --version))"
fi

# Install brew with packages & casks via Python CLI (packages.toml is source of truth)
print_section "Homebrew packages"
if command -v uv >/dev/null 2>&1; then
    uv run --project "$DOTFILES_DIR/cli" dotfiles brew install
else
    print_warn "Skipping brew install — uv not available (install uv and run: dotfiles brew install)"
fi

# Setup macos dock
"$DOTFILES_DIR/macos/dock.sh"
# Set file-type defaults (Zed for .md/.txt, etc.) — requires duti from packages.toml
"$DOTFILES_DIR/macos/file-associations.sh"
# Configure local LLM: download model + pin context window — requires lm-studio from packages.toml
"$DOTFILES_DIR/macos/lmstudio.sh"
# Login items for apps that don't self-register (Flycut)
"$DOTFILES_DIR/macos/login-items.sh"
################################################################################

# Languages & Runtimes
print_header "🔧 Languages & Runtimes"

# -- Go
print_section "Go"
if ! command -v go >/dev/null 2>&1; then
    print_info "Go not found (should be installed via packages.toml)"
else
    print_info "Go already installed ($(go version | awk '{print $3}'))"
fi
# -- Node.js / FNM (Fast Node Manager — installed via packages.toml)
print_section "Node.js / FNM"
if ! command -v fnm >/dev/null 2>&1; then
    print_info "FNM not found (should be installed via packages.toml)"
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
    
    # Stable symlinks for node/npx in /opt/homebrew/bin
    # GUI apps such as Claude Desktop can't find fnm-managed node because they
    # don't source .zshrc. Symlinks in a PATH they do search solve this.
    node_bin="$(command -v node 2>/dev/null)"
    npx_bin="$(command -v npx 2>/dev/null)"
    if [[ -n "$node_bin" && -d /opt/homebrew/bin ]]; then
        ln -sf "$node_bin" /opt/homebrew/bin/node
        ln -sf "$npx_bin" /opt/homebrew/bin/npx
        print_success "Node/npx symlinked to /opt/homebrew/bin (GUI app support)"
    fi
fi

# -- Python / UV
# Only install Python 3.14 if it's not already installed via UV
if command -v uv >/dev/null 2>&1 && ! command -v python3.14 >/dev/null 2>&1; then
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

# Yazi
print_section "Yazi"
if command -v yazi >/dev/null 2>&1; then
    mkdir -p ~/.config/yazi
    ln -sf "$DOTFILES_DIR/terminal/yazi/yazi.toml" ~/.config/yazi/yazi.toml 2>/dev/null || true
    print_success "Yazi configured (show_hidden enabled)"
else
    print_info "Yazi not installed — skipping config"
fi

# Zellij
print_section "Zellij"
if command -v zellij >/dev/null 2>&1; then
    mkdir -p ~/.config/zellij/layouts
    ln -sf "$DOTFILES_DIR/terminal/zellij/config.kdl" ~/.config/zellij/config.kdl 2>/dev/null || true
    ln -sf "$DOTFILES_DIR/terminal/zellij/layouts/mobile.kdl" ~/.config/zellij/layouts/mobile.kdl 2>/dev/null || true
    print_success "Zellij configured (minimal config + mobile deck layout)"
else
    print_info "Zellij not installed — skipping config"
fi

# Editor configurations
print_header "📝 Editor Configuration"

# Zed
if command -v zed >/dev/null 2>&1; then
    print_section "Zed"
    mkdir -p ~/.config/zed
    ln -sf "$DOTFILES_DIR/editors/zed/settings.json" ~/.config/zed/settings.json 2>/dev/null || true
    ln -sf "$DOTFILES_DIR/editors/zed/keymap.json" ~/.config/zed/keymap.json 2>/dev/null || true
    print_success "Zed configured (settings + keymap symlinked)"
fi

# Obsidian
OBSIDIAN_VAULT="$HOME/code/private/notes"
if [[ -d "$OBSIDIAN_VAULT/.obsidian" ]]; then
    print_section "Obsidian"
    OBSIDIAN_CONFIGS=(app appearance core-plugins daily-notes graph templates hotkeys)
    for cfg in "${OBSIDIAN_CONFIGS[@]}"; do
        local_file="$DOTFILES_DIR/editors/obsidian/${cfg}.json"
        vault_file="$OBSIDIAN_VAULT/.obsidian/${cfg}.json"
        _link "$local_file" "$vault_file"
    done
    # Community plugins
    chmod +x "$DOTFILES_DIR/editors/obsidian/plugins.sh"
    . "$DOTFILES_DIR/editors/obsidian/plugins.sh" "$OBSIDIAN_VAULT"
    print_success "Obsidian configured"
else
    print_info "Obsidian vault not found at $OBSIDIAN_VAULT — skipping config"
fi

if [[ -x "$OBSIDIAN_VAULT/bin/notes" ]]; then
    mkdir -p "$HOME/.local/bin"
    ln -sf "$OBSIDIAN_VAULT/bin/notes" "$HOME/.local/bin/notes"
    ln -sf "$OBSIDIAN_VAULT/bin/notes" "$HOME/.local/bin/nts"
    print_success "Notes CLI linked as notes and nts"
fi

# Workbench (Claude/Codex instructions, skills, MCP, hooks, and prompts)
print_header "🤖 Workbench"

print_section "Setup"
WORKBENCH_DIR="${WORKBENCH_DIR:-$HOME/code/public/workbench}"
if [[ ! -d "$WORKBENCH_DIR/.git" ]]; then
    print_action "Cloning workbench..."
    mkdir -p "$(dirname "$WORKBENCH_DIR")"
    if ! git clone https://github.com/e-m-albright/workbench.git "$WORKBENCH_DIR" \
        || ! git -C "$WORKBENCH_DIR" checkout --detach "$WORKBENCH_COMMIT"; then
        print_error "Workbench clone failed"
        exit 1
    fi
fi
mkdir -p "$HOME/.local/bin"
ln -sf "$WORKBENCH_DIR/bin/workbench" "$HOME/.local/bin/workbench"
ln -sf "$WORKBENCH_DIR/bin/workbench" "$HOME/.local/bin/wb"
# The workbench tool prints its own verbose banners and boxes (and has no quiet
# flag). Capture its output so this section stays in the installer's own visual
# language, replaying the raw output only when something actually fails.
if ! wb_out="$("$WORKBENCH_DIR/bin/workbench" sync all 2>&1)"; then
    printf '%s\n' "$wb_out"
    print_error "Workbench sync failed"
    exit 1
fi
if ! wb_out="$("$WORKBENCH_DIR/bin/workbench" drift all 2>&1)"; then
    printf '%s\n' "$wb_out"
    print_error "Workbench verification found managed drift"
    exit 1
fi
print_success "Workbench synced to Claude and Codex"

if command -v lefthook >/dev/null 2>&1; then
    # lefthook prints its own terse "sync hooks: ..." line; keep our vocabulary.
    if ! lh_out="$(lefthook install 2>&1)"; then
        printf '%s\n' "$lh_out"
        print_error "Git hook installation failed"
        exit 1
    fi
    print_success "Git hooks installed"
fi

# Clear cache (execute, don't source — avoids re-evaluating the CLI dispatcher
# in the installer's shell)
"$DOTFILES_DIR/bin/dotfiles" clean

mkdir -p "$HOME/code/public"

# Final completion message
print_completion "✨ Dotfiles setup complete!"
