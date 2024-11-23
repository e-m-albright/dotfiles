#!/bin/bash

# Setting PATH for Python 3.12
# The original version is saved in .zprofile.pysave
PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:${PATH}"
export PATH

# Bash completion
[[ -r "/usr/local/etc/profile.d/bash_completion.sh" ]] && . "/usr/local/etc/profile.d/bash_completion.sh"

# Node Version Manager
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Bun completions
[ -s "/Users/evan/.bun/_bun" ] && source "/Users/evan/.bun/_bun"

# Bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Rust
. "$HOME/.cargo/env"

# Python
# As a function becasue it's slow to load.
function py() {
    local PYENV_ROOT="$HOME/.pyenv"
    local VENV_DIR=".venv"

    # Initialize pyenv if not already done
    if ! command -v pyenv >/dev/null; then
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    fi

    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating new virtual environment..."
        # TODO python not python3
        python3 -m venv "$VENV_DIR"
    fi

    # Activate venv
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        echo "Virtual environment activated."
    else
        echo "Error: Virtual environment activation failed."
        return 1
    fi
}