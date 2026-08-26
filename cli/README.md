# dotfiles-cli

CLI for the dotfiles dev environment.

Run from repo root: `dotfiles <command>` (via `bin/dotfiles` shim → `uv run`).
Dev tasks: `just` (grouped help); `just check` (full gate); `just check --fast` (pre-commit, no tests); `just fmt --check`; `just scrub --artifacts` / `just scrub --caches`.

## Layout

Two load-bearing rules: `cli.py` renders, `service.py` decides.

- `app/` wires dependencies and the command tree.
- `cmd/<feature>/` holds each feature: `cli.py` (Typer rendering),
  `service.py` (decisions), plus whatever else the feature needs
  (`models.py` and colocated `test_*.py`).
- `adapters/` contains subprocess effects; `testing/` contains fakes.
