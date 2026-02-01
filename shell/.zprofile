# =============================================================================
# Login Shell Configuration
# =============================================================================
# Runs once when you log in. Sets up Homebrew and tool paths.

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
