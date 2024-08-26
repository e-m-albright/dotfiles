# Install Homebrew

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew update
brew upgrade

brew tap homebrew/cask-versions

# QOL Utilities
brew install tmux
brew install dockutil
brew install wifi-password
brew install bash-completion@2
# Git
brew install git
brew install git-lfs  # Large file support
# Dev Utilities
brew install htop     # Monitoring CPU, memory, and processes
brew install iftop    # Monitoring network traffic
brew install openssl  # SSL/TLS
brew install wget     # Downloading files
brew install jq       # JSON manipulation
brew install nmap     # Network scanning
# Programming Languages and Frameworks
brew install xz       # Compression - required for pyenv
brew install pyenv    # Python version manager
brew install bun      # JavaScript runtime

# Wait a bit before moving on...
sleep 1

# ...and then.
echo "Success! Basic brew packages are installed."

# Install cask packages

# Browsers
brew install --cask google-chrome
brew install --cask spotify
brew install --cask discord
brew install --cask zoom
# QOL tools
brew install --cask rectangle
brew install --cask flux
brew install --cask flycut
# brew install --cask raycast # TODO - I'm curious what this is about, worth trying
# Development tools
brew install --cask visual-studio-code
brew install --cask iterm2
brew install --cask docker
brew install --cask docker-compose
# brew install --cask postman
# brew install --cask insomnia
# Design tools
brew install --cask figma

# Quick Look Plugins (https://github.com/sindresorhus/quick-look-plugins)
brew cask install qlcolorcode qlstephen qlmarkdown quicklook-json qlprettypatch quicklook-csv betterzipql qlimagesize webpquicklook qlvideo

# Wait a bit before moving on...
sleep 1

# ...and then.
echo "Success! Brew additional applications are installed."