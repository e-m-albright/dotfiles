# tools/

Standalone Python CLIs that complement the rest of the dotfiles. Each tool is a self-contained UV-managed package; run with `uv run <name> --help` from the tool's directory, or `uv tool install <path>` to register globally.

## Current Tools

- **[yt-ingest](./yt-ingest/)** -- ingest YouTube bookmarks into the Obsidian Learn/ queue with Gemini + oEmbed verification.

## Adding a Tool

The convention is one directory per tool with this layout:

```
tools/<name>/
  pyproject.toml         # UV-managed, includes `[project.scripts]` entry
  README.md              # what it does, why, install + usage
  <name>/
    __init__.py
    __main__.py          # so `python -m <name>` works
    cli.py               # Typer app exported as `app`
    ...                  # supporting modules
```

Conventions for `pyproject.toml`:
- Python `>=3.11` minimum.
- Dependencies kept minimal (typer + rich is fine; pull more only when needed).
- `[project.scripts]` entry so `uv tool install` produces a globally callable command.
- No formal `ruff`/`lefthook` guards in this directory unless the tool grows complex enough to warrant it.

## Why Not in `bin/`?

`bin/` is reserved for the lightweight `dotfiles` shell utility and shims. Anything that needs Python (and a virtualenv) lives here so the dependency boundary is explicit.
