#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./macos/print_utils.sh
source "$SCRIPT_DIR/print_utils.sh"

DRY_RUN=false
KILL_SESSIONS=false

usage() {
    cat <<'EOF'
Usage: dotfiles remote-disable [options]

Disable this Mac's phone remote shell entrypoint by turning off macOS Remote Login.
Mosh stops working too because it bootstraps through SSH.

Options:
  --dry-run         Print actions without changing the system
  --kill-sessions   Also kill existing mosh-server and sshd sessions for this user
  -h, --help        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --kill-sessions)
            KILL_SESSIONS=true
            shift
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

remote_login_is_on() {
    command -v systemsetup >/dev/null 2>&1 && systemsetup -getremotelogin 2>/dev/null | grep -q "On"
}

kill_existing_sessions() {
    [[ "$KILL_SESSIONS" == true ]] || return 0

    local user_name
    user_name=$(id -un)

    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: pkill -u $user_name mosh-server"
        print_info "DRY RUN: pkill -u $user_name sshd"
        return 0
    fi

    pkill -u "$user_name" mosh-server 2>/dev/null || true
    pkill -u "$user_name" sshd 2>/dev/null || true
    print_success "Existing Mosh/SSH sessions killed"
}

print_header "Phone Remote Shell Disable"

if ! command -v systemsetup >/dev/null 2>&1; then
    print_warn "systemsetup not found. Turn off Remote Login manually in System Settings -> General -> Sharing"
    exit 0
fi

if ! remote_login_is_on; then
    print_success "Remote Login already disabled"
    kill_existing_sessions
    print_completion "Remote shell entrypoint is off"
    exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
    print_info "Remote Login will be disabled"
    print_info "DRY RUN: sudo systemsetup -setremotelogin off"
    kill_existing_sessions
    print_completion "Dry run complete"
elif [[ -t 0 ]] || sudo -n true 2>/dev/null; then
    print_action "sudo systemsetup -setremotelogin off"
    if output=$(sudo systemsetup -setremotelogin off 2>&1); then
        [[ -n "$output" ]] && print_info "$output"
        print_success "Remote Login disabled"
        kill_existing_sessions
        print_completion "Remote shell entrypoint is off"
    else
        print_warn "$output"
        print_warn "If macOS mentions Full Disk Access, use System Settings -> General -> Sharing -> Remote Login -> Off"
        exit 1
    fi
else
    print_warn "Needs sudo in an interactive terminal. Run manually: sudo systemsetup -setremotelogin off"
    print_warn "Or use System Settings -> General -> Sharing -> Remote Login -> Off"
fi
