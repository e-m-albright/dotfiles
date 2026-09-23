# <img src="assets/brand/icon.svg" alt="" width="48" /> Dotfiles

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

The installer is macOS-only and safe to rerun. Personal remains the default.
Its read-only plan can be validated on any host with `./install.sh --plan`. It:

1. Links the tracked shell and Git configuration.
2. Configures SSH and installs Homebrew when needed.
3. Reconciles packages from `macos/packages.toml`.
4. Applies macOS, Dock, terminal, and editor configuration.
5. Clones `~/code/public/workbench`, runs `workbench sync all`, and fails the
   install if `workbench drift all` detects managed drift.

Secrets and personal Git identity stay outside the repository. The installer
writes Git identity to `~/.gitconfig.local`.

For a lightweight work machine, use the fail-closed profile:

```bash
./install.sh --plan --profile work
./install.sh --profile work
```

The work profile installs only its explicit formula, cask, special-installer,
and npm allowlists from `macos/packages.toml`. It shares the personal zsh setup
with work-safe defaults and a short profile banner, adds Node.js LTS, uv-managed
Python 3.14, and tenv-managed Terraform; installs Rectangle, Flycut, Ghostty,
Caffeine, f.lux, TypeWhisper, Zed, Spotify, and OrbStack; keeps OrbStack on
demand; and syncs Workbench with `--profile work`. It does not apply personal
Git or SSH configuration, Dock, file associations, login items, private
automation, Zed settings, local models, Go, Rust, pnpm, or cache cleanup.

Work shells print a muted `dotfiles / profile=work  (profile_status for more)`
reminder by default. Run `profile_status` for the full local configuration view.
Set `DOTFILES_STARTUP_DETAIL=off|short|long` in `~/.zshrc.local` to change
the startup view. The [work data-flow registry](docs/work-profile-data-flows.md)
records which modes can transmit source, credentials, telemetry, or account
data and which organizational approvals remain open.

## Daily Commands

```text
dotfiles doctor                 live host, credential, and workbench drift check
dotfiles doctor --fix           repair supported symlinks and local config
dotfiles credential init        create the private metadata-only inventory
dotfiles credential list        show grants, consumers, scopes, and local status
dotfiles credential set ID      prompt securely and store one grant in Keychain
dotfiles credential link-pi ID  resolve one Pi provider grant from Keychain
dotfiles credential run ID --…  inject one grant into one child process
dotfiles brew install           install the default personal package set
dotfiles brew install --profile work
                                install only the explicit work allowlist
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
`workbench drift` compare desired state with the live machine directly, so there
is no stored observation to become stale. The credential inventory contains
private declarations, not observed status or secret values. See
[`docs/credentials.md`](docs/credentials.md).

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

oMLX is the active open-source Apple Silicon inference runner. Qwen3.6 is the
local Pi model. Serving, tool calling, structured output, and software-offline
checks have passed. The physical network-disconnect test remains open, and
operational accuracy supports supervised use only. Privacy also depends on the
agent's tools, logs, and backups; see [data hygiene](docs/privacy-data-hygiene.md).

LM Studio remains a tombstoned fallback. The current setup and historical
benchmarks live in [`docs/local-llm-stack.md`](docs/local-llm-stack.md); the
cross-platform model and provider ranking lives in Workbench's
[`open-model-inference.md`](https://github.com/e-m-albright/workbench/blob/main/playbook/knowledge/open-model-inference.md).

## Package Manifest

`macos/packages.toml` is the source of truth; unknown fields are rejected to
catch configuration typos before installation. Disabled entries preserve an
intentional absence: rejected tools, deferred installs, or clients that belong
on another device. They prevent casual reintroduction without falsely treating
every absence as a bad product. Keep the reason and date when disabling one.

Feature groups can be skipped per personal install:

```bash
dotfiles brew install --no-ai
dotfiles brew install --no-productivity
dotfiles brew install --no-social
```

Category flags are rejected with `--profile work`; the work profile is an exact
allowlist rather than a combination of personal categories.

## Repository Layout

```text
bin/                 thin `dotfiles` launcher
cli/                 Typer CLI
macos/               package manifest and system setup
shell/               zsh configuration and completions
terminal/            Ghostty and Yazi configuration
editors/             Zed host configuration
git/                 global Git configuration
docs/                machine-specific operating notes
```

## Development

The CLI uses Python 3.13+, Typer, Pydantic, and uv. Tests are colocated
with the modules they cover.

```bash
just verify          # complete project gate
just fmt             # focused formatting while iterating
just check           # Python static checks and tests
just test            # tests and coverage
just audit           # dependency vulnerabilities
just lint-shell      # ShellCheck
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
