# Dotfiles

My dotfiles!

TODO can I automate
- Final step of enabling rectangle
- Configure flux

TODO use the bin dotfiles or remove

https://eugeneyan.com/writing/mac-setup/
Apple ID: Sign in
MacOS update: Settings -> General -> Software Update
~~Keyboard: Switch to Dvorak, key repeat = fast, delay until repeat = short~~
~~Trackpad: Max tracking speed, tap to click, click = light, natural scroll = off~~
Displays: Switch to Apple Display (p3-600) for slightly better battery life
Finder: Show Library, show hidden files, show path bar

https://www.swyx.io/new-mac-setup
https://sourabhbajaj.com/mac-setup/
https://www.taniarascia.com/setting-up-a-brand-new-mac-for-development/
https://registerspill.thorstenball.com/p/new-year-new-job-new-machine
https://mimansajaiswal.github.io/posts/mac-softwares/

https://www.robinwieruch.de/mac-setup-web-development/
Do from command - https://www.robinwieruch.de/mac-setup-web-development/


# TODO - regret, installed caffeine don't like sticky bad software
Does it matter? maybe not. I do not like having software that's hard to remove

caffeine is built for Intel macOS and so requires Rosetta 2 to be installed.
You can install Rosetta 2 with:
    softwareupdate --install-rosetta --agree-to-license
Note that it is very difficult to remove Rosetta 2 once it is installed.

Rather just go with amphetamine but they don't offer a brew install


worth trying instead of oh-my-zsh: https://fishshell.com/


Try obsidian?
brew install --cask obsidian

# clone obsidian vault (i use obsidian-git for syncing)
git clone git@github.com:<github-username>/<obsidian-vault>.git


brew install ollama
ollama serve

# in another terminal, pull some models to try
ollama pull llama3.2 nemotron  # 3B and 70B respectively

# WTF is this
uv tool install open-webui
uv tool run open-webui serve

This thing?
https://www.raycast.com/ - replaces rectangle too, and the clipboard helper I got?

https://wisprflow.ai/ - dictation?


brew install --cask google-drive

brew install --cask vlc


Meh what?
brew install stats
brew install jordanbaird-ice


## Install

On a fresh installation of MacOS:

    sudo softwareupdate -i -a
    xcode-select --install

Clone and install dotfiles:
```
git clone https://github.com/e-m-albright/dotfiles ~/dotfiles
chmod +wx ~/dotfiles/install.sh
chmod -R +wx ~/dotfiles/bin
~/dotfiles/install.sh
```

## Additional steps

## The `dotfiles` command

    $ dotfiles
    ￫ Usage: dotfiles <command>

    Commands:
       help             This help message
       update           Update packages and pkg managers (OS, brew, npm, yarn, commposer)
       clean            Clean up caches (brew, npm, yarn, composer)
       symlinks         Run symlinks script
       brew             Run brew script
       hosts            Run hosts script
       defaults         Run MacOS defaults script
       dock             Run MacOS dock script

## Credits

* https://dotfiles.github.io/
* https://github.com/webpro/awesome-dotfiles

and

* https://github.com/Grsmto/dotfiles/tree/master
* https://github.com/lexicalunit/dotfiles
* https://github.com/Lissy93/dotfiles
* https://github.com/mihaliak/dotfiles
* https://github.com/webpro/dotfiles/tree/main
* https://github.com/mathiasbynens/dotfiles