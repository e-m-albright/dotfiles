# shellcheck shell=bash
# =============================================================================
# Login Shell Configuration
# =============================================================================
# Runs once when you log in. Sets up Homebrew and tool paths.

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Rust — sourced in .zshenv, no need to duplicate here
