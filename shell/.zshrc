# History Configuration
# ------------------------------------------------------------------
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt APPEND_HISTORY
setopt HIST_IGNORE_ALL_DUPS  # Don't record duplicates
setopt HIST_SAVE_NO_DUPS     # Don't save duplicates
setopt HIST_REDUCE_BLANKS    # Remove blank lines
setopt INC_APPEND_HISTORY    # Add commands as they are typed
setopt EXTENDED_HISTORY      # Add timestamps to history

# ZSH Options
# ------------------------------------------------------------------
setopt COMPLETE_IN_WORD     # Allow tab completion in the middle of a word
setopt AUTO_CD              # If a command is a directory, cd into it
setopt NO_CASE_GLOB         # Case insensitive globbing
setopt NUMERIC_GLOB_SORT    # Sort filenames numerically when it makes sense
setopt NO_BEEP              # No beep on error
setopt AUTO_REMOVE_SLASH    # Remove trailing slash when completing directory

# Homebrew Configuration
# ------------------------------------------------------------------
export PATH=/opt/homebrew/bin:$PATH
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_NO_ANALYTICS=1  # Disable analytics

# Oh My Zsh Configuration
# ------------------------------------------------------------------
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="amuse"

# Update Configuration
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 13

# History timestamp format
HIST_STAMPS="yyyy-mm-dd"

# Plugins
plugins=(
    aliases
    git
    tmux
    vscode
    # zsh-autosuggestions     # Suggests commands as you type
    # zsh-syntax-highlighting # Syntax highlighting in shell
    z                       # Jump to frequently used directories
)

source $ZSH/oh-my-zsh.sh

# Editor Configuration
# ------------------------------------------------------------------
if [[ -n $SSH_CONNECTION ]]; then
    export EDITOR='vim'
else
    export EDITOR='vim'
fi

# Aliases
# ------------------------------------------------------------------
# Search
alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'

# File System
alias l.='ls -d .*'
alias ll='ls -l'
alias la='ls -la'
alias lh='ls -lh'        # Human readable sizes
alias ldot='ls -ld .*'   # List hidden files only
alias lsd='ls -ld */'    # List directories only

# Navigation
alias downloads='cd ~/Downloads'
alias co='cd ~/code'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Git Aliases
# Import from git config
for al in $(git config --get-regexp '^alias\.' | cut -f 1 -d ' ' | cut -f 2 -d '.'); do
    alias g${al}="git ${al}"
done
unset al

# Additional Git shortcuts
alias gs='git status'
alias gp='git pull'
alias gst='git stash'
alias gcm='git commit -m'

# Development
alias mk="make"
alias py="python3"
alias pip="pip3"

# System
alias path='echo -e ${PATH//:/\\n}'  # Print each PATH entry on a separate line
alias ports='netstat -tulanp'        # Show active ports
alias mem='free -h'                  # Show memory usage

# Bun Configuration
# ------------------------------------------------------------------
# Use $HOME instead of hardcoded username
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# Functions
# ------------------------------------------------------------------
# Create a directory and cd into it
mkcd() {
    mkdir -p "$@" && cd "$_"
}

# Extract various compressed file types
extract() {
    if [ -f $1 ]; then
        case $1 in
            *.tar.bz2)   tar xjf $1     ;;
            *.tar.gz)    tar xzf $1     ;;
            *.bz2)       bunzip2 $1     ;;
            *.rar)       unrar e $1     ;;
            *.gz)        gunzip $1      ;;
            *.tar)       tar xf $1      ;;
            *.tbz2)      tar xjf $1     ;;
            *.tgz)       tar xzf $1     ;;
            *.zip)       unzip $1       ;;
            *.Z)         uncompress $1  ;;
            *.7z)        7z x $1        ;;
            *)          echo "'$1' cannot be extracted via extract()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}
# bun completions
[ -s "/Users/evan/.bun/_bun" ] && source "/Users/evan/.bun/_bun"

# fnm
eval "$(fnm env)"
