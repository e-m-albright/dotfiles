# Homebrew
export PATH=/opt/homebrew/bin:$PATH

# Get the directory these scripts live in, not the symlink origin
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# The language file is slower to load due to pyenv
# Test performance : `time ( source ~/dotfiles/shell/.zshrc_languages )`
source $SCRIPT_DIR/shell/.zshrc_languages
source $SCRIPT_DIR/shell/.zshrc_ohmyzsh
source $SCRIPT_DIR/shell/.zshrc_shorthands

# Save history
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt APPEND_HISTORY

# Allow tab completion in the middle of a word.
setopt COMPLETE_IN_WORD
