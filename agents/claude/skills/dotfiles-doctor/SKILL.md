---
name: dotfiles-doctor
description: Run dotfiles doctor to check system health and diagnose environment issues
---

# Dotfiles Doctor

Run `dotfiles doctor` to check that all tools, symlinks, and configurations are properly installed, then interpret the results and suggest fixes for any issues found.

## When to use

- User asks about missing tools or broken setup
- Debugging environment issues (wrong version, missing binary, broken symlink)
- After running `dotfiles install` or `dotfiles update` to verify success
- User asks "is everything set up correctly?"

## Workflow

1. Run the doctor command:

```bash
~/dotfiles/bin/dotfiles doctor
```

2. Parse the output for any failures or warnings
3. For each issue found:
   - Explain what's wrong and why it matters
   - Provide the specific fix command
   - Note any dependencies (e.g., "install Homebrew first")
4. If `dotfiles stale` is also relevant (e.g., user is cleaning up), run that too:

```bash
~/dotfiles/bin/dotfiles stale
```

5. Summarize: what's healthy, what needs attention, and the recommended order of fixes
