# Install Homebrew

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew update
brew upgrade

brew tap homebrew/cask-versions

# QOL Utilities
brew install dockutil
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
brew install uv       # Python
brew install bun      # JavaScript runtime

# Wait a bit before moving on...
sleep 1

# ...and then.
echo "Success! Basic brew packages are installed."

# Install cask packages

# Applications
brew install --cask google-chrome
brew install --cask spotify
brew install --cask discord
brew install --cask zoom
brew install --cask super-productivity
# QOL tools
brew install --cask rectangle   # Window manager
brew install --cask flux        # Night light
brew install --cask flycut      # Clipboard manager
# Development tools
brew install --cask visual-studio-code
brew install --cask cursor
brew install --cask iterm2
brew install --cask docker
brew install --cask docker-compose
# brew install --cask postman
# brew install --cask insomnia
# brew install --cask figma

# Quick Look Plugins (https://github.com/sindresorhus/quick-look-plugins)
brew cask install qlcolorcode qlstephen qlmarkdown quicklook-json qlprettypatch quicklook-csv betterzipql qlimagesize webpquicklook qlvideo

# Wait a bit before moving on...
sleep 1

# ...and then.
echo "Success! Brew additional applications are installed."