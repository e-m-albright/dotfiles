#!/bin/sh

dockutil --no-restart --remove all
dockutil --no-restart --add "/Applications/Google Chrome.app"
dockutil --no-restart --add "/Applications/Spotify.app"
dockutil --no-restart --add "/Applications/Visual Studio Code.app"
dockutil --no-restart --add "/Applications/Discord.app"

dockutil --add /Applications --display folder
dockutil --add ~/Downloads

killall Dock

echo "Success! Dock is set."