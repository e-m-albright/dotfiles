#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./print_utils.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/print_utils.sh"

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TYPEWHISPER_CONFIG_DIR="$DOTFILES_DIR/macos/typewhisper"
TYPEWHISPER_SUPPORT_DIR="$HOME/Library/Application Support/TypeWhisper"
TYPEWHISPER_PREFS="$HOME/Library/Preferences/com.typewhisper.mac.plist"
TYPEWHISPER_APP="/Applications/TypeWhisper.app"

usage() {
    printf "Usage: macos/typewhisper.sh apply [--quit] [--reopen]\n"
    printf "\n"
    printf "Commands:\n"
    printf "  apply           Apply tracked preferences and workflow configuration\n"
    printf "\n"
    printf "Options for apply:\n"
    printf "  --quit          Quit TypeWhisper before applying live SQLite-backed settings\n"
    printf "  --reopen        Reopen TypeWhisper after applying\n"
}

is_typewhisper_running() {
    pgrep -x "TypeWhisper" >/dev/null 2>&1
}

quit_typewhisper() {
    if ! is_typewhisper_running; then
        return 0
    fi

    print_action "Quitting TypeWhisper"
    osascript -e 'tell application "TypeWhisper" to quit' >/dev/null 2>&1 || true
    for _ in {1..30}; do
        if ! is_typewhisper_running; then
            print_success "TypeWhisper stopped"
            return 0
        fi
        sleep 0.2
    done

    print_error "TypeWhisper is still running; quit it manually and retry"
    return 1
}


apply_typewhisper() {
    local quit_first=false
    local reopen=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quit) quit_first=true ;;
            --reopen) reopen=true ;;
            -h|--help) usage; return 0 ;;
            *) print_error "Unknown option: $1"; usage; return 1 ;;
        esac
        shift
    done

    print_header "Applying TypeWhisper configuration"

    if [[ ! -d "$TYPEWHISPER_APP" ]]; then
        print_error "TypeWhisper.app is not installed"
        return 1
    fi

    if is_typewhisper_running; then
        if [[ "$quit_first" == true ]]; then
            quit_typewhisper
        else
            print_error "TypeWhisper is running"
            print_info "Run: macos/typewhisper.sh apply --quit --reopen"
            return 1
        fi
    fi

    print_section "Preferences and workflows"
    python3 "$DOTFILES_DIR/macos/typewhisper_apply.py" \
        "$TYPEWHISPER_CONFIG_DIR" "$TYPEWHISPER_PREFS" "$TYPEWHISPER_SUPPORT_DIR"
    print_success "Applied tracked TypeWhisper config"

    if command -v killall >/dev/null 2>&1; then
        killall cfprefsd >/dev/null 2>&1 || true
    fi

    if [[ "$reopen" == true ]]; then
        print_action "Reopening TypeWhisper"
        open -a "TypeWhisper"
    fi

    print_completion "TypeWhisper configuration applied"
}

command="${1:-help}"
shift || true
case "$command" in
    apply) apply_typewhisper "$@" ;;
    -h|--help|help) usage ;;
    *) print_error "Unknown TypeWhisper command: $command"; usage; exit 1 ;;
esac
