# Dotfiles

Personal macOS bootstrap and operating configuration. This repo turns a fresh
MacBook into the host environment I want: packages, shell, terminal, editors,
privacy utilities, and Tailscale-direct agent access.

Dotfiles is the base layer of a three-repository capability stack, described
canonically in workbench's
[`STACK.md`](https://github.com/e-m-albright/workbench/blob/main/STACK.md):

```text
dotfiles   host foundation and machine capabilities
    ↓
workbench  reusable agent intelligence and engineering standards
    ↓
notes      private knowledge and operating layer
```

Agent behavior and engineering guidance live in the separate
[`workbench`](https://github.com/e-m-albright/workbench) repo. Dotfiles installs
it and asks it to configure Claude Code and Codex, but does not duplicate that
logic. A private knowledge-and-operations layer sits above both public
repositories; its data and operating details are intentionally not published,
and neither public repository requires it. Each layer stands alone and
integrates through CLI contracts, not Python imports.

## Install

```bash
mkdir -p ~/code/public
git clone https://github.com/e-m-albright/dotfiles.git ~/code/public/dotfiles
~/code/public/dotfiles/install.sh
```

The installer is macOS-only and safe to rerun. It:

1. Links the tracked shell and Git configuration.
2. Configures SSH and installs Homebrew when needed.
3. Reconciles packages from `macos/packages.toml`.
4. Applies macOS, Dock, terminal, editor, and Obsidian configuration.
5. Clones `~/code/public/workbench`, runs `workbench sync all`, and fails the
   install if `workbench drift all` detects managed drift.

Secrets and personal Git identity stay outside the repository. The installer
writes Git identity to `~/.gitconfig.local`.

## Daily Commands

```text
dotfiles doctor                 live host and workbench drift check
dotfiles doctor --fix           repair supported symlinks and local config
dotfiles brew install           install missing declared packages
dotfiles brew stale             show undeclared installed packages
dotfiles brew prune             preview installed disabled tombstones
dotfiles brew prune --yes       uninstall disabled packages; keep tombstones
dotfiles brew upgrade           upgrade installed packages
dotfiles update                 update macOS, packages, and runtimes
dotfiles clean                  clean package caches
dotfiles dock                   reset the Dock layout
dotfiles profile-shell          profile shell startup
```

There are no machine-state snapshots. `doctor`, `brew stale`, and
`workbench drift` compares desired state with the live machine directly, so there
is no stored observation to become stale.

## Remote Control

The remote stack is intentionally limited to Tailscale, Paseo, and one tailnet-only private web surface. Paseo owns agent process continuity and the native mobile interface for Pi, Claude Code, and Codex. Tailscale Serve proxies the loopback web service over HTTPS on port 8443. There is no phone shell, terminal multiplexer, browser terminal, or Mission Control session manager.

```text
dotfiles remote status
dotfiles remote on
dotfiles remote off
dotfiles remote paseo
dotfiles remote tailscale
```

See [`docs/remote-shell.md`](docs/remote-shell.md) for setup and recovery details.

## Password Utility

`password` creates a random alphanumeric password (20 characters by default),
prints it, and copies it to the clipboard.

```text
dotfiles password [LENGTH] [--no-copy]
```

## Local Models

Not installed. LM Studio was trialled as the local-inference runner and removed
on 2026-07-25 — it worked fine, but local models stayed slower and weaker at
coding than hosted frontier models, so the weights weren't earning their disk.

The `lm-studio` entry in `macos/packages.toml` is tombstoned rather than deleted,
and the benchmarks that justified the choice are preserved in
[`docs/local-llm-stack.md`](docs/local-llm-stack.md) for whenever it's worth
another look.

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
cli/                 Typer CLI
macos/               package manifest and system setup
shell/               zsh configuration and completions
terminal/            Ghostty and Yazi configuration
editors/             Zed and Obsidian host configuration
git/                 global Git configuration
docs/                machine-specific operating notes
```


## Development

The CLI uses Python 3.13+, Typer, Pydantic, and uv. Tests are colocated
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

## Reuse

This is a personal setup, published as fork-and-adapt material rather than a
framework. If you want something similar, start from `macos/packages.toml` and
`install.sh`, replace the package choices and identity-specific pieces with
your own, and delete what you don't use. Nothing here is designed to be
depended on as a package.
