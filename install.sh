#!/bin/bash
set -euo pipefail

# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_install_plan() {
    local required
    if [[ "$PROFILE" == "work" ]]; then
        for required in \
            macos/packages.toml \
            macos/print_utils.sh \
            macos/link_utils.sh \
            macos/orbstack.sh \
            shell/.zprofile \
            shell/.zshenv \
            shell/.zshrc \
            shell/profile-status.zsh \
            shell/amuse.zsh-theme \
            terminal/ghostty.config; do
            if [[ ! -e "$DOTFILES_DIR/$required" ]]; then
                printf 'install plan: missing required input: %s\n' "$required" >&2
                return 1
            fi
        done
        cat <<'EOF'
Dotfiles macOS work install plan (read-only)

Selected Homebrew taps: none
Selected Homebrew formulae:
  git, git-lfs, git-delta, gh, jq, yq, ripgrep, fd, fzf, bat, zoxide, just,
  shellcheck, lefthook, gitleaks, fnm, uv, deno, awscli, tenv
Selected Homebrew casks: ghostty, zed, spotify, orbstack
Selected special installer: claude_code
Selected npm global: @earendil-works/pi-coding-agent
Runtimes: Node.js LTS via fnm; Python 3.14 via uv; Terraform via tenv
Configuration: shared shell configuration with a work profile; Ghostty; OrbStack
  on-demand; clone/link Workbench; sync and drift with --profile work

Skipped host mutations: default shell; Git configuration and identity; SSH; Dock,
file associations, and login items; private automation discovery; Zed settings;
oMLX/Qwen; Go and Rust tools; pnpm; package cache cleanup.

No host state was inspected or changed.
EOF
        return
    fi

    for required in \
        git/.gitconfig \
        git/.gitignore_global \
        shell/.zprofile \
        shell/.zshenv \
        shell/.zshrc \
        shell/profile-status.zsh \
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

PROFILE="personal"
PLAN=false
while (( $# )); do
    case "$1" in
        --plan)
            PLAN=true
            shift
            ;;
        --profile)
            if (( $# < 2 )) || [[ "$2" != "personal" && "$2" != "work" ]]; then
                printf 'Usage: install.sh [--plan] [--profile personal|work]\n' >&2
                exit 2
            fi
            PROFILE="$2"
            shift 2
            ;;
        *)
            printf 'Usage: install.sh [--plan] [--profile personal|work]\n' >&2
            exit 2
            ;;
    esac
done
if [[ "$PLAN" == true ]]; then
    print_install_plan
    exit
fi

# Fail clearly on a non-macOS host instead of cascading through chsh/defaults/
# softwareupdate/duti errors. The read-only plan above is intentionally portable
# so Linux CI can verify the installer's declared inputs and sequence.
if [[ "$OSTYPE" != darwin* ]]; then
    printf 'install.sh targets macOS (OSTYPE=%s). Aborting.\n' "$OSTYPE" >&2
    exit 1
fi

# Apply the same privacy defaults before the first Homebrew command; future
# interactive shells also set these in .zshrc.
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_ENV_HINTS=1

# Supply-chain pins for first-install bootstrap. Advance them deliberately
# (verify the new commit/version, then update). WORKBENCH_COMMIT pins the
# FRESH clone only — an existing ~/code/public/workbench is a live working
# repo and is deliberately left at whatever it has checked out.
OH_MY_ZSH_COMMIT="677a4592b18c08ddea737f8aca70bac0e9fc9313"
HOMEBREW_INSTALL_COMMIT="fea42d9aedd20a82bea800a6898dcde19401ab1f"
WORKBENCH_COMMIT="0652471e40f7c11ec68ea159d262565be4665376"

# Source shared installer functions.
source "$DOTFILES_DIR/macos/print_utils.sh"
source "$DOTFILES_DIR/macos/link_utils.sh"

if [[ "$PROFILE" == "work" ]]; then
    print_header "Work profile"

    print_section "Shell"
    if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
        print_action "Installing Oh My Zsh..."
        if ! RUNZSH=no sh -c "$(curl -fsSL "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/$OH_MY_ZSH_COMMIT/tools/install.sh")" >/dev/null 2>&1; then
            print_error "Oh My Zsh install failed — shared shell configuration requires it"
            exit 1
        fi
    fi
    safe_link "$DOTFILES_DIR/shell/.zprofile" "$HOME/.zprofile"
    safe_link "$DOTFILES_DIR/shell/.zshenv" "$HOME/.zshenv"
    safe_link "$DOTFILES_DIR/shell/.zshrc" "$HOME/.zshrc"
    safe_link "$DOTFILES_DIR/shell/amuse.zsh-theme" "$HOME/.oh-my-zsh/custom/themes/amuse.zsh-theme"
    mkdir -p "$HOME/.config/dotfiles"
    printf 'work\n' > "$HOME/.config/dotfiles/profile"
    printf '%s\n' "$DOTFILES_DIR" > "$HOME/.config/dotfiles/root"
    print_success "Shared shell configured for work"

    print_section "Homebrew"
    if ! command -v brew >/dev/null 2>&1; then
        print_action "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL "https://raw.githubusercontent.com/Homebrew/install/$HOMEBREW_INSTALL_COMMIT/install.sh")"
        eval "$(/opt/homebrew/bin/brew shellenv)"
        print_success "Homebrew installed"
    else
        print_info "Homebrew already installed ($(brew --version | head -1))"
    fi
    brew update >/dev/null 2>&1
    print_success "Homebrew index updated"

    print_section "uv (Python package manager)"
    if ! brew list --formula uv >/dev/null 2>&1; then
        print_action "Installing uv through Homebrew..."
        if ! brew install uv >/dev/null 2>&1; then
            print_error "Homebrew uv install failed — package reconciliation requires uv"
            exit 1
        fi
        hash -r
    fi
    if ! command -v uv >/dev/null 2>&1; then
        print_error "uv is unavailable after bootstrap — cannot reconcile packages"
        exit 1
    fi

    print_section "Work software allowlist"
    uv run --project "$DOTFILES_DIR/cli" dotfiles brew install --profile work

    print_section "Node.js / FNM"
    if ! command -v fnm >/dev/null 2>&1; then
        print_error "fnm is unavailable after package reconciliation"
        exit 1
    fi
    fnm install --lts >/dev/null 2>&1
    fnm use --install-if-missing lts-latest >/dev/null 2>&1
    fnm default lts-latest >/dev/null 2>&1
    print_success "Node.js LTS installed"

    print_section "Python"
    uv python install 3.14 >/dev/null 2>&1
    print_success "Python 3.14 installed"

    print_section "Terraform"
    if ! command -v tenv >/dev/null 2>&1; then
        print_error "tenv is unavailable after package reconciliation"
        exit 1
    fi
    tenv tf install latest >/dev/null 2>&1
    tenv tf use latest >/dev/null 2>&1
    print_success "Terraform installed and managed by tenv"

    print_section "Ghostty"
    if command -v ghostty >/dev/null 2>&1 || [[ -d "/Applications/Ghostty.app" ]]; then
        mkdir -p "$HOME/.config/ghostty"
        safe_link "$DOTFILES_DIR/terminal/ghostty.config" "$HOME/.config/ghostty/config"
        print_success "Ghostty configured"
    fi

    "$DOTFILES_DIR/macos/orbstack.sh"

    print_section "Workbench"
    WORKBENCH_DIR="${WORKBENCH_DIR:-$HOME/code/public/workbench}"
    if [[ ! -d "$WORKBENCH_DIR/.git" ]]; then
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
    if ! wb_out="$("$WORKBENCH_DIR/bin/workbench" sync all --profile work 2>&1)"; then
        printf '%s\n' "$wb_out"
        print_error "Workbench sync failed"
        exit 1
    fi
    if ! wb_out="$("$WORKBENCH_DIR/bin/workbench" drift all --profile work 2>&1)"; then
        printf '%s\n' "$wb_out"
        print_error "Workbench verification found managed drift"
        exit 1
    fi
    print_success "Workbench work profile synced"
    print_completion "Dotfiles work setup complete!"
    exit
fi

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

# Ensure uv is present (needed to run the Python CLI for brew install). Homebrew
# is the sole owner on macOS; uv's self-updater must not compete with it.
print_section "uv (Python package manager)"
if ! brew list --formula uv >/dev/null 2>&1; then
    print_action "Installing uv through Homebrew..."
    if ! brew install uv >/dev/null 2>&1; then
        print_error "Homebrew uv install failed — package reconciliation requires uv"
        exit 1
    fi
    hash -r
else
    print_info "uv already installed through Homebrew ($(uv --version))"
fi

# Install brew with packages & casks via Python CLI (packages.toml is source of truth)
print_section "Homebrew packages"
if ! command -v uv >/dev/null 2>&1; then
    print_error "uv is unavailable after bootstrap — cannot reconcile packages"
    exit 1
fi
uv run --project "$DOTFILES_DIR/cli" dotfiles brew install

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
    
    # pnpm 12 is a native binary; install it outside fnm's Corepack shims.
    if command -v npx >/dev/null 2>&1; then
        if PNPM_HOME="$HOME/.npm-global" npx --yes get-pnpm 12.1.0 >/dev/null 2>&1; then
            print_info "pnpm 12.1.0 installed"
        else
            print_warn "pnpm could not be installed; rerun the installer after checking Node"
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

# -- Terraform / tenv
if command -v tenv >/dev/null 2>&1; then
    tenv tf install latest >/dev/null 2>&1
    tenv tf use latest >/dev/null 2>&1
    print_success "Terraform installed and managed by tenv"
fi

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
        # Only select a primary checkout; linked worktrees are temporary.
        if [[ -x "$candidate" && -d "${candidate%/bin/notes}/.git" ]]; then
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
    if [[ -x "$PRIVATE_AUTOMATION_ROOT/bin/apple-contacts" ]]; then
        safe_link "$PRIVATE_AUTOMATION_ROOT/bin/apple-contacts" "$HOME/.local/bin/apple-contacts"
    fi
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
