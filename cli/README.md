# dotfiles-cli

CLI for the dotfiles dev environment.

Run from repo root: `dotfiles <command>` (via `bin/dotfiles` shim → `uv run`).
Dev tasks: `just` (grouped help); `just check` (full gate); `just check --fast` (pre-commit, no tests); `just fmt --check`; `just scrub --artifacts` / `just scrub --caches`.

## Layout

- `app/` wires dependencies and the command tree.
- `cmd/<feature>/cli.py` renders Typer commands.
- `cmd/<feature>/service.py` owns feature decisions.
- `adapters/` contains subprocess and launcher effects.
- `tui/` and feature `pane.py` files render Textual UI.
