# Get dotfiles dir (so run this script from anywhere)
export DOTFILES_DIR
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Install brew with packages & casks
. "$DOTFILES_DIR/macos/brew.sh"
# Setup macos dock
. "$DOTFILES_DIR/macos/dock.sh"

# Dotfile symlinks
ln -sfv "$DOTFILES_DIR/git/.gitconfig" ~
ln -sfv "$DOTFILES_DIR/shell/.zprofile" ~
ln -sfv "$DOTFILES_DIR/shell/.zshenv" ~
ln -sfv "$DOTFILES_DIR/shell/.zshrc" ~

# Vscode extensions & settings
. "$DOTFILES_DIR/vscode/extensions.sh"
ln -sfv "$DOTFILES_DIR/vscode/settings.json" ~/Library/Application\ Support/Code/User/settings.json

# Clear cache
. "$DOTFILES_DIR/bin/dotfiles" clean

# Add keys from keychain to ssh agent
ssh-add -A 2>/dev/null;
