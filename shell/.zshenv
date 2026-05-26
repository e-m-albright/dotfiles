# =============================================================================
# Environment Variables
# =============================================================================
# Loaded for all shell types. Keep minimal for performance.

# Rust
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# Dotfiles CLI + UV / Python tools
export PATH="$HOME/dotfiles/bin:$HOME/.local/bin:$PATH"
