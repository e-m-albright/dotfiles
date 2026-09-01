#!/bin/bash
set -euo pipefail

# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_install_plan() {
    local required
    for required in \
        git/.gitconfig \
        git/.gitignore_global \
        shell/.zprofile \
        shell/.zshenv \
        shell/.zshrc \
        shell/amuse.zsh-theme \
        bin/dotfiles \
        macos/packages.toml \
        macos/print_utils.sh \
        macos/link_utils.sh \
        macos/ssh.sh \
        macos/dock.sh \
        macos/file-associations.sh \
        macos/login-items.sh \
        macos/orbstack.sh \
        terminal/ghostty.config \
        terminal/yazi/yazi.toml \
        editors/zed/settings.json \
        editors/zed/keymap.json; do
        if [[ ! -e "$DOTFILES_DIR/$required" ]]; then
            printf 'install plan: missing required input: %s\n' "$required" >&2
            return 1
        fi
    done

    cat <<'EOF'
Dotfiles macOS install plan (read-only)

 1. Install Oh My Zsh and select zsh as the default shell
 2. Link tracked shell and Git configuration
 3. Configure local Git identity and SSH
 4. Bootstrap Homebrew and uv when absent
 5. Reconcile packages from macos/packages.toml
 6. Apply Dock, file association, login item, and OrbStack settings
 7. Reconcile Node.js and Python runtimes
 8. Link terminal, editor, and optional private-tool configuration
 9. Sync and verify Workbench configuration
10. Install Git hooks and clean package caches

No host state was inspected or changed.
EOF
}

case "$#" in
    0) ;;
    1)
        if [[ "$1" == "--plan" ]]; then
            print_install_plan
            exit
        fi
        printf 'Usage: install.sh [--plan]\n' >&2
        exit 2
        ;;
    *)
        printf 'Usage: install.sh [--plan]\n' >&2
        exit 2
        ;;
esac

# Fail clearly on a non-macOS host instead of cascading through chsh/defaults/
# softwareupdate/duti errors. The read-only plan above is intentionally portable
# so Linux CI can verify the installer's declared inputs and sequence.
if [[ "$OSTYPE" != darwin* ]]; then
    printf 'install.sh targets macOS (OSTYPE=%s). Aborting.\n' "$OSTYPE" >&2
    exit 1
fi
# Supply-chain pins for first-install bootstrap. Advance them deliberately
# (verify the new commit/version, then update). WORKBENCH_COMMIT pins the
# FRESH clone only — an existing ~/code/public/workbench is a live working
# repo and is deliberately left at whatever it has checked out.
OH_MY_ZSH_COMMIT="677a4592b18c08ddea737f8aca70bac0e9fc9313"
HOMEBREW_INSTALL_COMMIT="fea42d9aedd20a82bea800a6898dcde19401ab1f"
WORKBENCH_COMMIT="dfadab4f9f8f1cccfb2bb5ea4921b2627ef05367"
UV_VERSION="0.11.29"

# Source shared installer functions.
source "$DOTFILES_DIR/macos/print_utils.sh"
source "$DOTFILES_DIR/macos/link_utils.sh"

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
    if chsh -s "$(which zsh)" >/dev/null 2>&1; then
        print_success "Shell changed to zsh"
    else
        print_warn "chsh failed (often a password/PAM prompt) — run manually: chsh -s \$(which zsh)"
    fi
fi

# Dotfile symlinks. Unmanaged destinations are backed up, never overwritten.
print_section "Symlinks"
safe_link "$DOTFILES_DIR/git/.gitconfig" ~/.gitconfig
safe_link "$DOTFILES_DIR/git/.gitignore_global" ~/.gitignore_global
safe_link "$DOTFILES_DIR/shell/.zprofile" ~/.zprofile
safe_link "$DOTFILES_DIR/shell/.zshenv" ~/.zshenv
safe_link "$DOTFILES_DIR/shell/.zshrc" ~/.zshrc
safe_link "$DOTFILES_DIR/shell/amuse.zsh-theme" ~/.oh-my-zsh/custom/themes/amuse.zsh-theme

# Git identity setup (stored in ~/.gitconfig.local, not committed)
if [ ! -f ~/.gitconfig.local ]; then
    print_section "Git Identity"
    print_action "Setting up git identity..."
    git_name=""
    while [[ -z "$git_name" ]]; do
        printf "  Enter your full name: "
        read -r git_name
    done
    git_email=""
    while [[ -z "$git_email" ]]; do
        printf "  Enter your email: "
        read -r git_email
    done
    # git config writes the values as literal strings — an unquoted heredoc
    # here would command-substitute whatever the user typed.
    printf '# Local git identity (not committed to dotfiles repo)\n' > ~/.gitconfig.local
    git config --file ~/.gitconfig.local user.name "$git_name"
    git config --file ~/.gitconfig.local user.email "$git_email"
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

    # ~/.zprofile is already the tracked symlink that runs brew shellenv for
    # future shells; activate it for this session only.
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

# Granola updates faster than its Homebrew cask; keep it manually installed so
# bootstrap cannot replace a newer official build with an older cask version.
print_section "Manual application: Granola"
if [[ -d /Applications/Granola.app ]]; then
    print_success "Granola is installed and remains outside Homebrew management"
else
    print_warn "Install Granola manually from https://www.granola.ai/download"
fi

# Setup macos dock
"$DOTFILES_DIR/macos/dock.sh"
# Set file-type defaults (Zed for .md/.txt, etc.) — requires duti from packages.toml
"$DOTFILES_DIR/macos/file-associations.sh"
# Login items for apps that don't self-register (Flycut)
"$DOTFILES_DIR/macos/login-items.sh"
# Keep the OrbStack VM on-demand rather than resident at login
"$DOTFILES_DIR/macos/orbstack.sh"
################################################################################

# Languages & Runtimes
print_header "🔧 Languages & Runtimes"

# -- Node.js / FNM (fnm and go install via packages.toml; doctor reports presence)
print_section "Node.js / FNM"
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
    
    # Keep pnpm reproducible through Node's package-manager shim.
    if command -v corepack >/dev/null 2>&1; then
        if corepack enable >/dev/null 2>&1 && corepack install --global pnpm@10.11.1 >/dev/null 2>&1; then
            print_info "Corepack enabled (pnpm 10.11.1)"
        else
            print_warning "Corepack could not activate pnpm; rerun the installer after checking Node"
        fi
    fi
    
    # Stable symlinks for node/npx in /opt/homebrew/bin
    # GUI apps such as Claude Desktop can't find fnm-managed node because they
    # don't source .zshrc. Symlinks in a PATH they do search solve this.
    node_bin="$(command -v node 2>/dev/null)"
    npx_bin="$(command -v npx 2>/dev/null)"
    if [[ -n "$node_bin" && -n "$npx_bin" && -d /opt/homebrew/bin ]]; then
        safe_link "$node_bin" /opt/homebrew/bin/node
        safe_link "$npx_bin" /opt/homebrew/bin/npx
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
    safe_link "$DOTFILES_DIR/terminal/ghostty.config" ~/.config/ghostty/config
    print_success "Ghostty configured (notifications enabled)"
else
    print_info "Ghostty not installed — skipping config"
fi

# Yazi
print_section "Yazi"
if command -v yazi >/dev/null 2>&1; then
    mkdir -p ~/.config/yazi
    safe_link "$DOTFILES_DIR/terminal/yazi/yazi.toml" ~/.config/yazi/yazi.toml
    print_success "Yazi configured (show_hidden enabled)"
else
    print_info "Yazi not installed — skipping config"
fi

# Editor configurations
print_header "📝 Editor Configuration"

# Zed
if command -v zed >/dev/null 2>&1; then
    print_section "Zed"
    mkdir -p ~/.config/zed
    safe_link "$DOTFILES_DIR/editors/zed/settings.json" ~/.config/zed/settings.json
    safe_link "$DOTFILES_DIR/editors/zed/keymap.json" ~/.config/zed/keymap.json
    print_success "Zed configured (settings + keymap symlinked)"
fi

# Discover one optional private automation layer without publishing its name.
PRIVATE_AUTOMATION_ROOT="${PRIVATE_AUTOMATION_ROOT:-}"
if [[ -z "$PRIVATE_AUTOMATION_ROOT" ]]; then
    for candidate in "$HOME"/code/private/*/bin/notes; do
        if [[ -x "$candidate" ]]; then
            PRIVATE_AUTOMATION_ROOT="${candidate%/bin/notes}"
            break
        fi
    done
fi
if [[ -x "$PRIVATE_AUTOMATION_ROOT/bin/notes" ]]; then
    mkdir -p "$HOME/.local/bin"
    safe_link "$PRIVATE_AUTOMATION_ROOT/bin/notes" "$HOME/.local/bin/notes"
    safe_link "$PRIVATE_AUTOMATION_ROOT/bin/notes" "$HOME/.local/bin/nts"
    print_success "Private knowledge CLI linked as notes and nts"
    for bridge in apple-notes apple-contacts; do
        if [[ -x "$PRIVATE_AUTOMATION_ROOT/bin/$bridge" ]]; then
            safe_link "$PRIVATE_AUTOMATION_ROOT/bin/$bridge" "$HOME/.local/bin/$bridge"
        fi
    done
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
safe_link "$WORKBENCH_DIR/bin/workbench" "$HOME/.local/bin/workbench"
safe_link "$WORKBENCH_DIR/bin/workbench" "$HOME/.local/bin/wb"
safe_link "$WORKBENCH_DIR/bin/wf" "$HOME/.local/bin/wf"
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
