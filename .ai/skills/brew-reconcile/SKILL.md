---
name: brew-reconcile
description: Compare installed Homebrew packages against `~/dotfiles/macos/packages.toml` source-of-truth and report drift in both directions. Use when user invokes /brew-reconcile, asks about Homebrew drift, wants an audit of installed vs declared packages, or says "what brew packages are stale", "what's missing", or "is my brew in sync with dotfiles?".
disable-model-invocation: true
---

# Brew Reconcile

Compare what's actually installed via Homebrew against the source-of-truth package lists in `~/dotfiles/macos/packages.toml`. Report drift in both directions.

## Workflow

1. Run `dotfiles brew stale` — this reports both directions of drift:
   - Installed but not declared in `packages.toml` (candidates for addition or removal)
   - Declared in `packages.toml` but not installed (run `dotfiles brew install` to fix)

```bash
dotfiles brew stale
```

2. Review the output and edit `~/dotfiles/macos/packages.toml` to reconcile:
   - Add packages you intentionally installed but haven't declared yet
   - Remove packages you no longer want tracked
   - Run `dotfiles brew install` to install anything declared but missing

3. Summarize counts and suggest next steps

## Notes

- `packages.toml` (not `brew.sh`, which has been removed) is the source of truth for declared packages
- `dotfiles brew stale` uses `brew leaves` for top-level packages — Homebrew dependencies are ignored
- Never auto-install or auto-remove — report only, then let the user decide
