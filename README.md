# Dotfiles

Personal macOS bootstrap and operating configuration. This repo turns a fresh
MacBook into the host environment I want: packages, shell, terminal, editors,
privacy utilities, local models, and remote session control.

Agent behavior and engineering guidance live in the separate
[`workbench`](https://github.com/e-m-albright/workbench) repo. Dotfiles installs
it and asks it to configure Claude Code and Codex, but does not duplicate that
logic.

## Install

```bash
mkdir -p ~/code/public
git clone https://github.com/e-m-albright/dotfiles.git ~/code/public/dotfiles
~/code/public/dotfiles/install.sh
```

The installer is macOS-only and safe to rerun. It:

1. Links the tracked shell and Git configuration.
2. configures SSH and installs Homebrew when needed.
3. Reconciles packages from `macos/packages.toml`.
4. Applies macOS, Dock, terminal, editor, and Obsidian configuration.
5. Clones `~/code/public/workbench`, runs `workbench sync all`, and fails the
   install if `workbench check all` detects managed drift.

Secrets and personal Git identity stay outside the repository. The installer
writes Git identity to `~/.gitconfig.local`.

## Daily Commands

```text
dotfiles doctor                 live host and workbench drift check
dotfiles doctor --fix           repair supported symlinks and local config
dotfiles brew install           install missing declared packages
dotfiles brew stale             show undeclared installed packages
dotfiles brew upgrade           upgrade installed packages
dotfiles update                 update macOS, packages, and runtimes
dotfiles clean                  clean package caches
dotfiles dock                   reset the Dock layout
dotfiles profile-shell          profile shell startup
```

There are no machine-state snapshots. `doctor`, `brew stale`, and
`workbench check` compare desired state with the live machine directly, so there
is no stored observation to become stale.

## Remote Control

The remote stack is Tailscale + Mosh/SSH + Zellij. Mission Control exposes the
same operations in a phone-friendly TUI and shows active Claude/Codex processes
beside their sessions.

```text
dotfiles remote status
dotfiles remote on
dotfiles remote off
dotfiles session ls
dotfiles session new NAME
dotfiles session attach NAME
dotfiles session kill NAME
dotfiles tui
```

See [`docs/remote-shell.md`](docs/remote-shell.md) for setup and recovery details.

## Email Masking

`email-mask` is a small privacy convenience around iCloud Hide My Email. The
default command creates an alias and copies it to the clipboard.

```text
dotfiles email-mask
dotfiles email-mask create [LABEL]
dotfiles email-mask list
dotfiles email-mask deactivate ADDRESS_OR_ID
dotfiles email-mask delete ADDRESS_OR_ID [--yes]
```

Set `DOTFILES_APPLE_ID` or pass `--apple-id`. Authentication is handled by
`pyicloud`; credentials are stored in the macOS keychain, never this repo.

## Local Models

LM Studio remains part of the machine setup for local inference, but the old
benchmark command was removed. Model fit and speed are easy to inspect directly
in LM Studio or with upstream tools when an evaluation is actually needed.

See [`docs/local-llm-stack.md`](docs/local-llm-stack.md) and
[`docs/lm-studio-local-models.md`](docs/lm-studio-local-models.md).

## Package Manifest

`macos/packages.toml` is the source of truth. Disabled entries preserve an
intentional absence: rejected tools, deferred installs, or clients that belong
on another device. They prevent casual reintroduction without falsely treating
every absence as a bad product. Keep the reason and date when disabling one.

Feature groups can be skipped per install:

```bash
dotfiles brew install --no-ai
dotfiles brew install --no-productivity
dotfiles brew install --no-social
```

## Repository Layout

```text
bin/                 thin `dotfiles` launcher
cli/                 Typer CLI and Textual Mission Control TUI
macos/               package manifest and system setup
shell/               zsh configuration and completions
terminal/            Ghostty, Zellij, direnv, and related config
editors/             Zed and Obsidian host configuration
git/                 global Git configuration
docs/                machine-specific operating notes
```


## Development

The CLI uses Python 3.13+, Typer, Textual, Pydantic, and uv. Tests are colocated
with the modules they cover.

```bash
just fmt
just check
just test
just audit
just lint-shell
```

The repo deliberately has no custom health scorecard, scheduled AI audit, or
project-bootstrap framework. Those concerns belong in workbench or in the
project that adopts them.
