#!/bin/bash
set -euo pipefail

# Source shared print functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/print_utils.sh"

# Check if dockutil is installed
if ! command -v dockutil >/dev/null 2>&1; then
    print_warn "dockutil is not installed. Please install it first:"
    print_action "brew install dockutil"
    exit 1
fi

print_header "⚓ Dock Configuration"

# Dock behavior
print_section "Preferences"
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0.5
defaults write com.apple.dock show-recents -bool false
defaults write com.apple.dock tilesize -int 72
print_success "Auto-hide enabled (no delay, fast animation, no recents)"

# Desired dock, in left-to-right order. This list is DECLARATIVE: the dock is
# pruned to exactly these apps (anything else in the apps section is removed).
# Deliberately omitted (launched via terminal/Raycast, or live in the menu bar):
# Tailscale, TypeWhisper, LM Studio, Slack.
apps=(
    "/Applications/Google Chrome.app"
    "/Applications/Obsidian.app"
    "/Applications/Spotify.app"
    "/Applications/Zed.app"
    "/Applications/Claude.app"
    "/Applications/Ghostty.app"
)

# Resolve desired labels (basename without .app) for installed apps only.
desired_labels=()
print_section "Applications"
for app in "${apps[@]}"; do
    if [ -e "$app" ]; then
        desired_labels+=("$(basename "$app" .app)")
    else
        print_warn "$app not found (skipping)"
    fi
done

# Current apps-section labels, in dock order.
current_labels=()
while IFS=$'\t' read -r label _ section _; do
    [ "$section" = "persistentApps" ] && current_labels+=("$label")
done < <(dockutil --list)

# Compare desired vs current (order-sensitive). Rebuild only on drift.
desired_joined="$(printf '%s\n' "${desired_labels[@]}")"
current_joined="$(printf '%s\n' "${current_labels[@]}")"

dock_changed=false
if [ "$desired_joined" = "$current_joined" ]; then
    print_info "Dock already matches desired set (${#desired_labels[@]} apps)"
else
    # Remove every current app, then re-add the desired set in order. This
    # guarantees both contents and ordering converge, and prunes extras.
    for label in "${current_labels[@]}"; do
        dockutil --no-restart --remove "$label" >/dev/null 2>&1 || true
    done
    for app in "${apps[@]}"; do
        [ -e "$app" ] || continue
        dockutil --no-restart --add "$app" >/dev/null 2>&1
        print_success "$(basename "$app" .app)"
    done
    dock_changed=true
fi

# Add special folders (idempotent)
print_section "Folders"
if dockutil --list | grep -q "Downloads"; then
    print_info "Downloads folder already in dock"
else
    dockutil --no-restart --add ~/Downloads >/dev/null 2>&1
    print_success "Added Downloads folder"
    dock_changed=true
fi

# Only restart Dock if changes were made (prevents window focus switching)
if [ "$dock_changed" = true ]; then
    print_action "Restarting Dock..."
    killall Dock 2>/dev/null || true
    sleep 0.5
fi
