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
    "/Applications/Visual Studio Code.app"
    "/Applications/Cursor.app"
    "/Applications/iTerm.app"
    "/Applications/Discord.app"
)

# Clear the dock
echo "Removing existing dock items..."
dockutil --no-restart --remove all
echo "✓ Dock cleared"

# Add applications
echo "Adding applications to dock..."
for app in "${apps[@]}"; do
    if [ -e "$app" ]; then
        dockutil --no-restart --add "$app"
        echo "✓ Added $(basename "$app")"
    else
        echo "⚠️  Warning: $app not found"
    fi
done

# Add special folders
echo "Adding folders to dock..."
dockutil --add /Applications --display folder
echo "✓ Added Applications folder"
dockutil --add ~/Downloads
echo "✓ Added Downloads folder"

# Restart Dock to apply changes
echo "Restarting Dock..."
killall Dock
echo "✓ Dock configuration complete!"