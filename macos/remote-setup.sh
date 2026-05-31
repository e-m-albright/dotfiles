#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./macos/print_utils.sh
source "$SCRIPT_DIR/print_utils.sh"

DRY_RUN=false
HARDEN_SSH=false
PHONE_PUBLIC_KEY=""
SESSION_NAME="mobile"

usage() {
    cat <<'EOF'
Usage: dotfiles remote-setup [options]

Set up this Mac as a phone-friendly SSH/Mosh/Zellij target for Termius.

Options:
  --dry-run             Print actions without changing the system
  --add-key <pubkey>    Add a Termius-generated public key to authorized_keys
  --harden-ssh          Disable password auth and enable pubkey auth for sshd
  --session <name>      Zellij session name to attach/create (default: mobile)
  -h, --help            Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --add-key)
            PHONE_PUBLIC_KEY="${2:-}"
            if [[ -z "$PHONE_PUBLIC_KEY" ]]; then
                print_error "--add-key requires a public key"
                exit 1
            fi
            shift 2
            ;;
        --harden-ssh)
            HARDEN_SSH=true
            shift
            ;;
        --session)
            SESSION_NAME="${2:-}"
            if [[ -z "$SESSION_NAME" ]]; then
                print_error "--session requires a name"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

run_or_print() {
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: $*"
    else
        print_action "$*"
        "$@"
    fi
}

run_sudo_or_warn() {
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: sudo $*"
    elif [[ -t 0 ]] || sudo -n true 2>/dev/null; then
        print_action "sudo $*"
        sudo "$@"
    else
        print_warn "Needs sudo in an interactive terminal. Run manually: sudo $*"
    fi
}

ensure_brew_package() {
    local package="$1"
    local command_name="$2"

    if command -v "$command_name" >/dev/null 2>&1; then
        print_success "$package available ($("$command_name" --version 2>/dev/null | head -1 || printf installed))"
        return 0
    fi

    if ! command -v brew >/dev/null 2>&1; then
        print_error "Homebrew is required to install $package"
        exit 1
    fi

    run_or_print brew install "$package"
}

ensure_ssh_dir() {
    local ssh_dir="$HOME/.ssh"
    local authorized_keys="$ssh_dir/authorized_keys"

    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: mkdir -p $ssh_dir"
        print_info "DRY RUN: chmod 700 $ssh_dir"
        print_info "DRY RUN: touch $authorized_keys"
        print_info "DRY RUN: chmod 600 $authorized_keys"
        return 0
    fi

    mkdir -p "$ssh_dir"
    chmod 700 "$ssh_dir"
    touch "$authorized_keys"
    chmod 600 "$authorized_keys"
    print_success "SSH authorized_keys ready"
}

add_phone_key() {
    local authorized_keys="$HOME/.ssh/authorized_keys"

    if [[ -z "$PHONE_PUBLIC_KEY" ]]; then
        print_warn "No phone key provided. Generate one in Termius, then rerun with --add-key '<public key>'"
        return 0
    fi

    if [[ "$PHONE_PUBLIC_KEY" != ssh-ed25519\ * && "$PHONE_PUBLIC_KEY" != ssh-rsa\ * && "$PHONE_PUBLIC_KEY" != ecdsa-sha2-* ]]; then
        print_error "--add-key does not look like an SSH public key"
        exit 1
    fi

    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: append phone public key to $authorized_keys if missing"
        return 0
    fi

    if grep -Fqx "$PHONE_PUBLIC_KEY" "$authorized_keys" 2>/dev/null; then
        print_success "Phone public key already present"
    else
        printf '%s\n' "$PHONE_PUBLIC_KEY" >> "$authorized_keys"
        print_success "Added phone public key to authorized_keys"
    fi
}

enable_remote_login() {
    if ! command -v systemsetup >/dev/null 2>&1; then
        print_warn "systemsetup not found. Enable Remote Login manually in System Settings"
        return 0
    fi

    if systemsetup -getremotelogin 2>/dev/null | grep -q "On"; then
        print_success "Remote Login already enabled"
    else
        run_sudo_or_warn systemsetup -setremotelogin on
    fi
}

harden_ssh() {
    local config_dir="/etc/ssh/sshd_config.d"
    local config_file="$config_dir/90-dotfiles-remote.conf"
    local content
    content=$'PubkeyAuthentication yes\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n'

    if [[ "$HARDEN_SSH" != true ]]; then
        print_warn "SSH password auth unchanged. Rerun with --harden-ssh after adding your Termius key"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: sudo mkdir -p $config_dir"
        print_info "DRY RUN: write key-only SSH config to $config_file"
        print_info "DRY RUN: sudo launchctl kickstart -k system/com.openssh.sshd"
        return 0
    fi

    if [[ -t 0 ]] || sudo -n true 2>/dev/null; then
        sudo mkdir -p "$config_dir"
        printf '%s' "$content" | sudo tee "$config_file" >/dev/null
        sudo chmod 644 "$config_file"
        sudo launchctl kickstart -k system/com.openssh.sshd 2>/dev/null || true
        print_success "SSH hardened for key-only login"
    else
        print_warn "Needs sudo in an interactive terminal. Run manually: sudo mkdir -p $config_dir"
        print_warn "Then write key-only SSH config to $config_file"
    fi
}

print_connection_info() {
    local user_name host_name tailnet_ip mosh_server command
    user_name=$(id -un)
    host_name=$(scutil --get LocalHostName 2>/dev/null || hostname -s)
    tailnet_ip=""
    if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
        tailnet_ip=$(tailscale ip -4 2>/dev/null | head -1 || true)
    fi

    if [[ -x /opt/homebrew/bin/mosh-server ]]; then
        mosh_server="/opt/homebrew/bin/mosh-server"
    else
        mosh_server="$(command -v mosh-server 2>/dev/null || printf /opt/homebrew/bin/mosh-server)"
    fi

    command="mosh --server=$mosh_server $user_name@$host_name -- zellij attach --create $SESSION_NAME"

    print_section "Termius setup"
    print_info "Host: $host_name"
    if [[ -n "$tailnet_ip" ]]; then
        print_info "Tailscale IP: $tailnet_ip"
    else
        print_warn "Tailscale does not look connected. Start Tailscale before connecting from your phone"
    fi
    print_info "Username: $user_name"
    print_info "Protocol: Mosh"
    print_info "Startup command: zellij attach --create $SESSION_NAME"
    printf "\nPaste into Termius as the Mosh command:\n%s\n" "$command"
}

print_header "Phone Remote Shell Setup"

print_section "Packages"
ensure_brew_package mosh mosh
ensure_brew_package zellij zellij

print_section "SSH server"
ensure_ssh_dir
add_phone_key
enable_remote_login
harden_ssh

print_connection_info
print_completion "Remote shell setup ready"
