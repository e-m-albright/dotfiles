# dotfiles-cli

CLI for the dotfiles dev environment.

Run `dotfiles <command>` through the `bin/dotfiles` shim. Python commands use
the synced virtual environment when present, with `uv run` as the fallback.

Run `just` for grouped help and `just verify` for the complete project gate.
`just check` runs Python checks and tests; `just check --fast` skips tests for
pre-commit. Use `just fmt --check` to check formatting and
`just scrub --caches` to remove generated caches. `just scrub --artifacts`
deletes local working notes under the ignored documentation directories.

## Layout

Two load-bearing rules: `cli.py` renders, `service.py` decides.

- `app/` wires dependencies and the command tree.
- `cmd/<feature>/` holds each feature: `cli.py` (Typer rendering),
  `service.py` (decisions), plus whatever else the feature needs
  (`models.py` and colocated `test_*.py`).
- `adapters/` contains subprocess effects; `testing/` contains fakes.
