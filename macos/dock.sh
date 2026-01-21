#!/bin/bash
set -euo pipefail

# Check if dockutil is installed
if ! command -v dockutil >/dev/null 2>&1; then
    echo "Error: dockutil is not installed. Please install it first:"
    echo "brew install dockutil"
    exit 1
fi

echo "Configuring Dock..."

# Apps to add to dock
apps=(
    "/Applications/Google Chrome.app"
    "/Applications/Spotify.app"
    "/Applications/Super Productivity.app"
    "/Applications/Cursor.app"
    "/Applications/Discord.app"
)

# Track if any changes were made (to avoid unnecessary Dock restart)
dock_changed=false

# Add applications (idempotent - only adds if not already present)
echo "Ensuring applications are in dock..."
for app in "${apps[@]}"; do
    if [ -e "$app" ]; then
        # Check if app is already in dock
        if dockutil --list | grep -q "$(basename "$app" .app)"; then
            echo "• $(basename "$app") already in dock"
        else
            dockutil --no-restart --add "$app" >/dev/null 2>&1
            echo "✓ Added $(basename "$app")"
            dock_changed=true
        fi
    else
        echo "⚠️  Warning: $app not found (skipping)"
    fi
done

# Add special folders (idempotent)
echo "Ensuring folders are in dock..."
if dockutil --list | grep -q "Downloads"; then
    echo "• Downloads folder already in dock"
else
    dockutil --no-restart --add ~/Downloads >/dev/null 2>&1
    echo "✓ Added Downloads folder"
    dock_changed=true
fi

# Only restart Dock if changes were made (prevents window focus switching)
if [ "$dock_changed" = true ]; then
    echo "Restarting Dock..."
    killall Dock 2>/dev/null || true
    sleep 0.5
    echo "✓ Dock configuration complete!"
else
    echo "✓ Dock configuration complete! (no changes needed)"
fi