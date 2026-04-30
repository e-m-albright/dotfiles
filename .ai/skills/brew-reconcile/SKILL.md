---
name: brew-reconcile
description: Compare installed Homebrew packages against brew.sh source-of-truth lists and report drift
disable-model-invocation: true
---

# Brew Reconcile

Compare what's actually installed via Homebrew against the source-of-truth package lists in `~/dotfiles/macos/brew.sh`. Report drift in both directions.

## Workflow

1. Parse `~/dotfiles/macos/brew.sh` to extract declared formulae and casks (both enabled and commented-out/disabled)

2. Get installed packages:

```bash
brew list --formulae
brew list --cask
```

3. Compare and report:

```
## Installed but not in brew.sh (candidates for addition or removal)
- package-name (formula)
  → Add to brew.sh if intentional, or: brew uninstall package-name

## In brew.sh but not installed
- package-name (formula)
  → Run: dotfiles brew (or: brew install package-name)

## Disabled in brew.sh but still installed (stale)
- package-name (cask, commented out in brew.sh)
  → Run: brew uninstall --cask package-name
```

4. Summarize counts and suggest next steps

## Notes

- This complements `dotfiles stale` which checks a hardcoded list — this skill dynamically parses brew.sh
- Ignore Homebrew dependencies (packages installed as deps of other packages) — use `brew leaves` for top-level only
- Never auto-install or auto-remove — report only
