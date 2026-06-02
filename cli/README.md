# dotfiles-cli

CLI for the dotfiles dev environment.

Run from repo root: `dotfiles <command>` (via `bin/dotfiles` shim → `uv run`).
Dev tasks: `just` (grouped help); `just check` (full gate); `just check --fast` (pre-commit, no tests); `just fmt --check`; `just scrub --artifacts` / `just scrub --caches`.
