# =============================================================================
# Environment Variables
# =============================================================================
# Loaded for all shell types. Keep minimal for performance.

# Rust
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# Dotfiles CLI + user-installed Python and Go tools
export PATH="$HOME/code/public/dotfiles/bin:$HOME/.local/bin:$HOME/go/bin:$PATH"
