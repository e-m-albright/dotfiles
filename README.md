# Dotfiles

My dotfiles!

TODO can I automate
- Final step of enabling rectangle
- Configure flux

TODO use the bin dotfiles or remove

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