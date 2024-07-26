#!/bin/bash

# Setting PATH for Python 3.12
# The original version is saved in .zprofile.pysave
PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:${PATH}"
export PATH

# # Bash completion
# [[ -r "/usr/local/etc/profile.d/bash_completion.sh" ]] && . "/usr/local/etc/profile.d/bash_completion.sh"

# # Node Version Manager
# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
# [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# # Bun completions
# [ -s "/Users/evan/.bun/_bun" ] && source "/Users/evan/.bun/_bun"

# # Bun
# export BUN_INSTALL="$HOME/.bun"
# export PATH="$BUN_INSTALL/bin:$PATH"

# # Rust
# . "$HOME/.cargo/env"

# # Python
# # This is slow to load.
# export PYENV_ROOT="$HOME/.pyenv"
# command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
# eval "$(pyenv init -)"