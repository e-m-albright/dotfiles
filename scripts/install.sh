#!/bin/bash
set -euo pipefail

export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# shellcheck source=lib/host.sh
source "$DOTFILES_DIR/scripts/lib/host.sh"
PROFILE=""
PLAN=false
while (( $# )); do
    case "$1" in
        --plan) PLAN=true; shift ;;
        --profile)
            if (( $# < 2 )) || [[ "$2" != personal && "$2" != work ]]; then
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

resolve_host_profile "$PROFILE"

# shellcheck source=../config/runtimes.conf
source "$DOTFILES_DIR/config/runtimes.conf"

print_install_plan() {
    local required profiles _label source _destination _required_tool python
    for required in config/packages.toml config/links.tsv config/runtimes.conf \
        scripts/lib/output.sh scripts/lib/links.sh scripts/lib/host.sh \
        scripts/macos/orbstack.sh config/zsh/profile-status.zsh bin/dotfiles; do
        if [[ ! -e "$DOTFILES_DIR/$required" ]]; then
            printf 'install plan: missing required input: %s\n' "$required" >&2
            return 1
        fi
    done
    while IFS=$'\t' read -r profiles _label source _destination _required_tool; do
        [[ -z "$profiles" || "$profiles" == \#* ]] && continue
        [[ ",$profiles," == *",$PROFILE,"* ]] || continue
        if [[ ! -e "$DOTFILES_DIR/$source" ]]; then
            printf 'install plan: missing required input: %s\n' "$source" >&2
            return 1
        fi
    done < "$DOTFILES_DIR/config/links.tsv"
    if [[ "$PROFILE" == work ]]; then
        # Never provision Python for a read-only plan. Prefer the existing CLI
        # interpreter, then explicitly verify system python3 has stdlib TOML.
        python="$DOTFILES_DIR/cli/.venv/bin/python"
        if [[ ! -x "$python" ]] || ! "$python" -c 'import tomllib' 2>/dev/null; then
            python=python3
            if ! command -v "$python" >/dev/null 2>&1 || ! "$python" -c 'import tomllib' 2>/dev/null; then
                printf 'install plan requires an existing Python 3.11+ with tomllib; no software was installed.\n' >&2
                return 1
            fi
        fi
        printf 'Dotfiles macOS work install plan (read-only)\n\n'
        "$python" "$DOTFILES_DIR/scripts/install-plan.py" "$DOTFILES_DIR/config/packages.toml"
        cat <<EOF
Runtimes: Node.js $NODE_VERSION via fnm; Python $PYTHON_VERSION via uv; Terraform via tenv
Configuration: shared shell configuration with a work profile; Ghostty; OrbStack
  on-demand; clone/link Workbench; sync and drift with --profile work

Skipped host mutations: default shell; Git configuration and identity; SSH; Dock,
file associations, and login items; private automation discovery; Zed settings;
oMLX/Qwen; Go and Rust tools; pnpm; package cache cleanup.
EOF
    else
        for required in scripts/macos/ssh.sh scripts/macos/dock.sh \
            scripts/macos/file-associations.sh scripts/macos/login-items.sh; do
            if [[ ! -e "$DOTFILES_DIR/$required" ]]; then
                printf 'install plan: missing required input: %s\n' "$required" >&2
                return 1
            fi
        done
        cat <<EOF
Dotfiles macOS install plan (read-only)

 1. Install Oh My Zsh and select zsh as the default shell
 2. Link tracked shell and Git configuration
 3. Configure local Git identity and SSH
 4. Bootstrap Homebrew and uv when absent
 5. Reconcile packages from config/packages.toml
 6. Apply Dock, file association, login item, and OrbStack settings
 7. Reconcile Node.js $NODE_VERSION, Python $PYTHON_VERSION, and pnpm $PNPM_VERSION
 8. Link terminal, editor, and optional private-tool configuration
 9. Sync and verify Workbench configuration
10. Install Git hooks and clean package caches
EOF
    fi
    printf '\nNo host state was changed.\n'
}

if [[ "$PLAN" == true ]]; then
    print_install_plan
    exit
fi
if [[ "$OSTYPE" != darwin* ]]; then
    printf 'install.sh targets macOS (OSTYPE=%s). Aborting.\n' "$OSTYPE" >&2
    exit 1
fi

export HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_ENV_HINTS=1
# Advance supply-chain pins deliberately after verifying the upstream revision.
OH_MY_ZSH_COMMIT="677a4592b18c08ddea737f8aca70bac0e9fc9313"
HOMEBREW_INSTALL_COMMIT="fea42d9aedd20a82bea800a6898dcde19401ab1f"
WORKBENCH_COMMIT="63dc1ffa3aaa1625d74462b1f3e224b5fe30dca5"
source "$DOTFILES_DIR/scripts/lib/output.sh"
source "$DOTFILES_DIR/scripts/lib/links.sh"

activate_homebrew() {
    local candidate
    if command -v brew >/dev/null 2>&1; then return 0; fi
    if [[ -n "${HOMEBREW_PREFIX:-}" && -x "$HOMEBREW_PREFIX/bin/brew" ]]; then
        eval "$("$HOMEBREW_PREFIX/bin/brew" shellenv)"
        return 0
    fi
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [[ -x "$candidate" ]]; then
            eval "$("$candidate" shellenv)"
            return 0
        fi
    done
    return 1
}

bootstrap_packages() {
    print_section "Homebrew"
    if activate_homebrew; then
        print_info "Homebrew already installed ($(brew --version | head -1))"
    else
        print_action "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL "https://raw.githubusercontent.com/Homebrew/install/$HOMEBREW_INSTALL_COMMIT/install.sh")"
        if ! activate_homebrew; then
            print_error "Homebrew is unavailable after installation"
            exit 1
        fi
        print_success "Homebrew installed"
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
    print_section "Homebrew packages"
    uv run --project "$DOTFILES_DIR/cli" dotfiles brew install --profile "$PROFILE"
}

configure_runtimes() {
    local fnm_env
    print_section "Node.js / FNM"
    if command -v fnm >/dev/null 2>&1; then
        fnm_env="$(fnm env)"
        eval "$fnm_env"
        fnm install "$NODE_VERSION" >/dev/null 2>&1
        fnm use --install-if-missing "$NODE_VERSION" >/dev/null 2>&1
        fnm default "$NODE_VERSION" >/dev/null 2>&1
        print_success "Node.js $NODE_VERSION installed"
        if [[ "$PROFILE" == personal ]]; then
            if command -v npx >/dev/null 2>&1; then
                if PNPM_HOME="$HOME/.npm-global" npx --yes get-pnpm "$PNPM_VERSION" >/dev/null 2>&1; then
                    print_info "pnpm $PNPM_VERSION installed"
                else
                    print_warn "pnpm could not be installed; rerun the installer after checking Node"
                fi
            fi
            # GUI applications do not source the shell's fnm environment.
            local node_bin npx_bin
            node_bin="$(command -v node 2>/dev/null)"
            npx_bin="$(command -v npx 2>/dev/null)"
            if [[ -n "$node_bin" && -n "$npx_bin" && -d /opt/homebrew/bin ]]; then
                safe_link "$FNM_DIR/aliases/default/bin/node" /opt/homebrew/bin/node
                safe_link "$FNM_DIR/aliases/default/bin/npx" /opt/homebrew/bin/npx
            fi
        fi
    elif [[ "$PROFILE" == work ]]; then
        print_error "fnm is unavailable after package reconciliation"
        exit 1
    fi
    print_section "Python"
    if [[ "$PROFILE" == work ]] || ! command -v "python$PYTHON_VERSION" >/dev/null 2>&1; then
        uv python install "$PYTHON_VERSION" >/dev/null 2>&1
        print_success "Python $PYTHON_VERSION installed"
    else
        print_info "Python $PYTHON_VERSION already installed"
    fi
    print_section "Terraform"
    if [[ "$PROFILE" == work ]] && command -v terraform >/dev/null 2>&1; then
        print_info "Terraform already installed ($(terraform version | head -1))"
    elif command -v tenv >/dev/null 2>&1; then
        if ! tenv tf install latest; then
            print_error "Terraform download failed — check the network connection and rerun the installer"
            exit 1
        fi
        if ! tenv tf use latest; then
            print_error "tenv could not activate the installed Terraform version"
            exit 1
        fi
        print_success "Terraform installed and managed by tenv"
    elif [[ "$PROFILE" == work ]]; then
        print_error "tenv is unavailable after package reconciliation"
        exit 1
    fi
}

attach_workbench_main() {
    local directory="$1"
    if git -C "$directory" symbolic-ref --quiet HEAD >/dev/null 2>&1; then return 0; fi
    print_action "Reattaching Workbench to main..."
    if git -C "$directory" show-ref --verify --quiet refs/heads/main; then
        git -C "$directory" checkout main
    else
        git -C "$directory" checkout -b main --track origin/main
    fi
}

configure_workbench() {
    print_section "Workbench"
    local directory="${WORKBENCH_DIR:-$HOME/code/public/workbench}" wb_out verb
    set --
    if [[ "$PROFILE" == work ]]; then set -- --profile work; fi
    if [[ ! -d "$directory/.git" ]]; then
        mkdir -p "$(dirname "$directory")"
        if ! git clone https://github.com/e-m-albright/workbench.git "$directory" \
            || ! git -C "$directory" checkout -B main "$WORKBENCH_COMMIT"; then
            print_error "Workbench clone failed"
            exit 1
        fi
    fi
    if ! attach_workbench_main "$directory"; then
        print_error "Workbench could not attach to main"
        exit 1
    fi
    mkdir -p "$HOME/.local/bin"
    safe_link "$directory/bin/workbench" "$HOME/.local/bin/workbench"
    safe_link "$directory/bin/workbench" "$HOME/.local/bin/wb"
    safe_link "$directory/bin/wf" "$HOME/.local/bin/wf"
    for verb in sync drift; do
        if ! wb_out="$("$directory/bin/workbench" "$verb" all "$@" 2>&1)"; then
            printf '%s\n' "$wb_out"
            print_error "Workbench $verb failed"
            exit 1
        fi
    done
    print_success "Workbench synced and verified"
}

print_section "Shell"
if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
    print_action "Installing Oh My Zsh..."
    if ! RUNZSH=no sh -c "$(curl -fsSL "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/$OH_MY_ZSH_COMMIT/tools/install.sh")" >/dev/null 2>&1; then
        if [[ "$PROFILE" == work ]]; then
            print_error "Oh My Zsh install failed — shared shell configuration requires it"
            exit 1
        fi
        print_warn "Oh My Zsh install failed — continuing anyway"
    fi
fi
if [[ "$PROFILE" == personal && "$SHELL" != "$(which zsh)" ]]; then
    if chsh -s "$(which zsh)" >/dev/null 2>&1; then
        print_success "Shell changed to zsh"
    else
        print_warn "chsh failed (often a password/PAM prompt) — run manually: chsh -s \$(which zsh)"
    fi
fi
link_host_configuration shell
write_host_markers

if [[ "$PROFILE" == personal ]]; then
    if [[ ! -f "$HOME/.gitconfig.local" ]]; then
        print_section "Git Identity"
        git_name=""
        while [[ -z "$git_name" ]]; do printf '  Enter your full name: '; read -r git_name; done
        git_email=""
        while [[ -z "$git_email" ]]; do printf '  Enter your email: '; read -r git_email; done
        printf '# Local git identity (not committed to dotfiles repo)\n' > "$HOME/.gitconfig.local"
        git config --file "$HOME/.gitconfig.local" user.name "$git_name"
        git config --file "$HOME/.gitconfig.local" user.email "$git_email"
    fi
    "$DOTFILES_DIR/scripts/macos/ssh.sh"
fi
bootstrap_packages
if [[ "$PROFILE" == personal ]]; then
    "$DOTFILES_DIR/scripts/macos/dock.sh"
    "$DOTFILES_DIR/scripts/macos/file-associations.sh"
    "$DOTFILES_DIR/scripts/macos/login-items.sh"
    "$DOTFILES_DIR/scripts/macos/orbstack.sh"
fi
configure_runtimes
link_host_configuration tools
if [[ "$PROFILE" == work ]]; then
    "$DOTFILES_DIR/scripts/macos/orbstack.sh"
fi

if [[ "$PROFILE" == personal ]]; then
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
        if [[ -x "$PRIVATE_AUTOMATION_ROOT/bin/apple-contacts" ]]; then
            safe_link "$PRIVATE_AUTOMATION_ROOT/bin/apple-contacts" "$HOME/.local/bin/apple-contacts"
        fi
    fi
fi
configure_workbench
if [[ "$PROFILE" == work ]]; then
    print_completion "Dotfiles work setup complete!"
    exit
fi
if command -v lefthook >/dev/null 2>&1; then
    if ! lh_out="$(lefthook install 2>&1)"; then
        printf '%s\n' "$lh_out"
        print_error "Git hook installation failed"
        exit 1
    fi
    print_success "Git hooks installed"
fi
"$DOTFILES_DIR/bin/dotfiles" clean
mkdir -p "$HOME/code/public"
print_completion "✨ Dotfiles setup complete!"
