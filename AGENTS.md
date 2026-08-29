# Dotfiles Repository

Personal macOS bootstrap and host configuration. Shared agent behavior and
engineering guidance are maintained in the sibling `workbench` repository.
`CATALOGUE.md` is a timestamped capability-health snapshot, refreshed on demand
rather than maintained during routine implementation.

## Project Context

This repo owns the host layer:

- `install.sh` - idempotent bootstrap entrypoint
- `macos/` - package manifest, system preferences, and bootstrap scripts
- `shell/`, `terminal/`, `git/` - command-line environment
- `editors/` - host editor configuration
- `bin/` - the `dotfiles`/`dfs` shim that routes to bash-native commands or the
  Python CLI (load-bearing: half the daily commands pass through it)
- `cli/` - the `dotfiles` Typer CLI
- `docs/` - machine-specific operating notes

It does not own agent rules, skills, MCP definitions, prompts, engineering
doctrine, or project health kits. Those belong in
`~/code/public/workbench`. Exception, documented here deliberately: a few
agent-launcher conveniences live in `shell/.zshrc` and `editors/zed/settings.json`
because they are vendor-native host config; the `cc` wrappers depend on
`~/.claude/profiles/*.json`, which `workbench sync` deploys.

## Invariants

- `macos/packages.toml` is the source of truth for installed software. Disabled
  entries are tombstones and retain a dated reason (machine-checked by the
  manifest model and `macos/test_packages_manifest.py`).
- Scripts are macOS-only where appropriate, idempotent, quote expansions, and use
  `set -eo pipefail` (`set -euo pipefail` when safe).
- Shell user-facing output uses `macos/print_utils.sh`; Python uses
  `dotfiles.console`.
- New CLI commands are Typer commands under `cli/src/dotfiles/cmd/`.
- `dotfiles doctor` checks live desired state. Do not introduce stored machine
  snapshots to detect drift.
- Remote access is deliberately limited to Tailscale-direct Paseo lifecycle and health plus one loopback-only private site proxied by Tailscale Serve. Never enable Funnel. Do not reintroduce a phone shell, terminal multiplexer, browser terminal, or Mission Control without a demonstrated need.
- Never commit secrets or personal Git identity. `~/.gitconfig.local` stays local.

## Verification

```bash
just verify        # check + lint-shell + audit + privacy-sweep, in one command
```

Keep changes small. This repository intentionally has no custom health ratchet,
scheduled AI audit, or multi-vendor agent framework.

## Working on the CLI

- The justfile runs from `cli/` (`set working-directory := 'cli'`); run recipes
  from anywhere in the repo.
- Tests are colocated next to their modules. Single module:
  `cd cli && uv run pytest src/dotfiles/cmd/doctor/`.
- `bin/dotfiles` routes bash-native commands (`update`, `clean`, `dock`, `profile-shell`) and delegates the rest to the Python CLI. `app/test_command_tree.py` keeps shim, help, and zsh completions in sync.
- Install git hooks once with `lefthook install`.

## Privacy (public repo)

This repo is public. `just privacy-sweep` enforces the rules below (it runs in
pre-commit and CI): no `/Users/<name>` paths in tracked files, and no term from
the machine-local denylist `~/.config/dotfiles/private-terms.txt` — private
project names live only in that gitignored file, never in the repo.

- Never reference a private project by name in tracked files — use generic phrasing ("a private project", "an internal manifesto").
- No hardcoded `/Users/<name>/...` home paths — use `~` / `$HOME`; test fixtures use `/home/dev`.
- `docs/adr/`, `docs/specs/`, `docs/plans/`, and `docs/superpowers/` are gitignored (local working notes); in-flight specs stay on disk, durable rationale graduates into `docs/` ADRs/guides — don't re-track them.
- Keep it neutral — no employment / status signals.
- Caveat: prior git *history* may still contain previously-scrubbed content; true removal needs a history rewrite (filter-repo/BFG) + force push.
