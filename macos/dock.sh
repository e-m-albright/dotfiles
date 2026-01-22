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
# Apps to add to dock
apps=(
    "/Applications/Google Chrome.app"
    "/Applications/Spotify.app"
    "/Applications/Linear.app"
    "/Applications/Cursor.app"
    "/Applications/Warp.app"
    "/Applications/Raycast.app"
    "/Applications/Claude.app"
    "/Applications/OrbStack.app"
)

# Track if any changes were made (to avoid unnecessary Dock restart)
dock_changed=false

# Add applications (idempotent - only adds if not already present)
print_section "Applications"
for app in "${apps[@]}"; do
    if [ -e "$app" ]; then
        # Check if app is already in dock
        if dockutil --list | grep -q "$(basename "$app" .app)"; then
            print_info "$(basename "$app") already in dock"
        else
            dockutil --no-restart --add "$app" >/dev/null 2>&1
            print_success "Added $(basename "$app")"
            dock_changed=true
        fi
    else
        print_warn "$app not found (skipping)"
    fi
done

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