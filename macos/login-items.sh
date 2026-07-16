#!/bin/bash
set -euo pipefail

# Source shared print functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/print_utils.sh"

print_header "🚪 Login Items"

# Apps that should auto-start at login and DON'T manage their own login item
# reliably. Additive only: apps that self-register (Tailscale, Caffeine,
# Rectangle, etc.) are left alone.
apps=(
    "/Applications/Flycut.app"
)

print_section "Applications"
current="$(osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null || echo "")"
for app in "${apps[@]}"; do
    name="$(basename "$app" .app)"
    if [ ! -e "$app" ]; then
        print_warn "$app not found (skipping)"
    elif [[ "$current" == *"$name"* ]]; then
        print_skip "$name already a login item"
    else
        osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$app\", hidden:false}" >/dev/null
        print_success "Added $name to login items"
    fi
done
