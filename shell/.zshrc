# Homebrew
export PATH=/opt/homebrew/bin:$PATH

# Save history
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt APPEND_HISTORY

# Allow tab completion in the middle of a word.
setopt COMPLETE_IN_WORD

# Load oh-my-zsh
# ------------------------------------------------------------------
# ------------------------------------------------------------------

export ZSH="$HOME/.oh-my-zsh"
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="amuse"
zstyle ':omz:update' mode auto      # update automatically without asking
zstyle ':omz:update' frequency 13
# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"
HIST_STAMPS="yyyy-mm-dd"

# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(aliases git tmux vscode)

source $ZSH/oh-my-zsh.sh

# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
  # Remote
  export EDITOR='vim'
else
  # Local
  export EDITOR='vim'
fi

# My own aliases
# ------------------------------------------------------------------
# ------------------------------------------------------------------

# Colorize search results
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'
alias grep='grep --color=auto'

# File system
alias l.='ls -d .*'  # list hidden files
alias ll='ls -l'     # list long

# Directories
alias downloads='cd ~/Downloads'
alias co='cd ~/code'

# Pull aliases from git config - complementary to oh-my-zsh
for al in $(git config --get-regexp '^alias\.' | cut -f 1 -d ' ' | cut -f 2 -d '.'); do
  alias g${al}="git ${al}"
done
unset al

# Extra Git
alias gs='git status'

# Shortcuts
alias mk="make"

# bun completions
[ -s "/Users/evan/.bun/_bun" ] && source "/Users/evan/.bun/_bun"
