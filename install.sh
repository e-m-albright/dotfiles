# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install oh-my-zsh if not already installed
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Installing Oh My Zsh..."
    RUNZSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    echo "✓ Oh My Zsh installed"
fi

# Set zsh as default shell
if [ "$SHELL" != "$(which zsh)" ]; then
    echo "Setting zsh as default shell..."
    chsh -s $(which zsh)
    echo "✓ Shell changed to zsh"
fi

# Dotfile symlinks
ln -sfv "$DOTFILES_DIR/git/.gitconfig" ~
ln -sfv "$DOTFILES_DIR/shell/.zprofile" ~
ln -sfv "$DOTFILES_DIR/shell/.zshenv" ~
ln -sfv "$DOTFILES_DIR/shell/.zshrc" ~
ln -fv "$DOTFILES_DIR/shell/amuse.zsh-theme" ~/.oh-my-zsh/custom/themes/amuse.zsh-theme

################################################################################
# Set up SSH for Git + Homebrew
. "$DOTFILES_DIR/macos/ssh.sh"
# Install brew with packages & casks
. "$DOTFILES_DIR/macos/brew.sh"
# Setup macos dock
. "$DOTFILES_DIR/macos/dock.sh"
################################################################################

# Languages
# -- Rust
if ! command -v rustc >/dev/null 2>&1; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    echo "✓ Rust installed"
fi

# -- JavaScript / Bun
if ! command -v bun >/dev/null 2>&1; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
    echo "✓ Bun installed"
fi

# -- Python / UV
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✓ UV installed"
fi

# Only install Python 3.12 if it's not already installed via UV
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Installing Python 3.12 via UV..."
    uv python install 3.12
    echo "✓ Python 3.12 installed"
fi

# Vscode extensions & settings
. "$DOTFILES_DIR/vscode/extensions.sh"
ln -sfv "$DOTFILES_DIR/vscode/settings.json" ~/Library/Application\ Support/Code/User/settings.json

# Clear cache
. "$DOTFILES_DIR/bin/dotfiles" clean

# Add keys from keychain to ssh agent
ssh-add -A 2>/dev/null;

