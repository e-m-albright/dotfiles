# =============================================================================
# Environment Variables
# =============================================================================
# Loaded for all shell types. Keep minimal for performance.

# Rust
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# UV / Python tools
export PATH="$HOME/.local/bin:$PATH"
