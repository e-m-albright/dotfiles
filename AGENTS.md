# Dotfiles Repository

Personal macOS bootstrap and host configuration. Shared agent behavior and
engineering guidance are maintained in the sibling `workbench` repository.

## Project Context

This repo owns the host layer:

- `macos/` - package manifest, system preferences, and bootstrap scripts
- `shell/`, `terminal/`, `git/` - command-line environment
- `editors/` - host editor and Obsidian configuration
- `cli/` - the `dotfiles` Typer CLI and Mission Control Textual TUI
- `docs/` - machine-specific operating notes

It does not own agent rules, skills, MCP definitions, prompts, engineering
doctrine, project health kits, or automations. Those belong in
`~/code/public/workbench`.

## Invariants

- `macos/packages.toml` is the source of truth for installed software. Disabled
  entries are tombstones and retain a dated reason.
- Scripts are macOS-only where appropriate, idempotent, quote expansions, and use
  `set -eo pipefail` (`set -euo pipefail` when safe).
- Shell user-facing output uses `macos/print_utils.sh`; Python uses
  `dotfiles.console`.
- New CLI commands are Typer commands under `cli/src/dotfiles/cmd/`.
- `dotfiles doctor` checks live desired state. Do not introduce stored machine
  snapshots to detect drift.
- Remote/session management and Mission Control are core capabilities.
- Never commit secrets or personal Git identity. `~/.gitconfig.local` stays local.

## Verification

Use the existing recipes:

```bash
just check
just lint-shell
just audit
```

Keep changes small. This repository intentionally has no custom health ratchet,
scheduled AI audit, or multi-vendor agent framework.

## Privacy (public repo)

This repo is public. Before committing, `git grep -niI` for any private-project names or personal absolute paths and ensure tracked files return nothing.

- Never reference a private project by name in tracked files — use generic phrasing ("a private project", "an internal manifesto").
- No hardcoded `/Users/<name>/...` home paths — use `~` / `$HOME`.
- `docs/specs/` and `docs/plans/` are gitignored (local working notes); in-flight specs stay on disk, durable rationale graduates into `docs/` ADRs/guides — don't re-track them.
- Keep it neutral — no employment / status signals.
- Caveat: prior git *history* may still contain previously-scrubbed content; true removal needs a history rewrite (filter-repo/BFG) + force push.
