# AGENTS.md
# Cross-platform instructions for AI coding agents
# Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot
#
# This file follows the AGENTS.md specification (https://agents.md)
# Keep this file under 500 lines. Reference external docs when needed.

<!-- ============================================================
     HOW TO USE THIS FILE
     ============================================================

     1. SYMLINK to your project root:
        ln -s ~/dotfiles/prompts/{recipe}/AGENTS.md ./AGENTS.md

     2. CREATE a ABSTRACT.md in your project root describing
        what you're building (see templates/ABSTRACT.md)

     3. The agent will read both files to understand your project
     ============================================================ -->

## Research & Library Usage

**Check the current date before researching.** Your training data may be stale.

- When looking up how to use a library, framework, or API: **search for the latest documentation first**. Do not assume your built-in knowledge reflects the current version.
- Check for breaking changes, new features, deprecations, and migration guides since your training cutoff.
- Look up the library's current best practices and ensure usage is optimal — don't just get it working, get it working *well*.
- If a library has moved to a new major version (e.g., Svelte 5, Pydantic v2, React 19), verify you're using the new API, not the old one.

## Git & GitHub CLI (`gh`)

Use the `gh` CLI for GitHub operations when available:

```bash
# Create PRs with structured descriptions
gh pr create --title "feat: add user auth" --body "## Summary\n- Added OAuth flow\n- Session management\n\n## Test plan\n- [ ] Manual login test"

# Check CI status before merging
gh pr checks <pr-number>

# Review and merge
gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash

# Create issues from the terminal
gh issue create --title "Bug: login redirect" --body "Steps to reproduce..."
```

When committing, write clear commit messages: imperative mood, explain *why* not *what*. Use conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
