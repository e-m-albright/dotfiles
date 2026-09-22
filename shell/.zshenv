# =============================================================================
# Environment Variables
# =============================================================================
# Loaded for all shell types. Keep minimal for performance.

# Host profile and checkout location. Work installs write these two small marker
# files; personal hosts retain the defaults.
DOTFILES_PROFILE="personal"
DOTFILES_DIR="$HOME/code/public/dotfiles"
if [[ -r "$HOME/.config/dotfiles/profile" ]]; then
    IFS= read -r DOTFILES_PROFILE < "$HOME/.config/dotfiles/profile"
fi
if [[ -r "$HOME/.config/dotfiles/root" ]]; then
    IFS= read -r DOTFILES_DIR < "$HOME/.config/dotfiles/root"
fi
export DOTFILES_PROFILE DOTFILES_DIR

# Rust
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# Dotfiles CLI + user-installed Python, npm, and Go tools
export PATH="$DOTFILES_DIR/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/go/bin:$PATH"
