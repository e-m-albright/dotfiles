# Cursor AI Rules

This file can be copied to `.cursorrules` in a project root to configure Cursor's AI behavior.

## Recommended Approach

**Don't use this file directly.** Instead, use the AGENTS.md from the appropriate recipe:

```bash
# For SvelteKit/TypeScript projects
cp ~/dotfiles/prompts/typescript/AGENTS.md .cursorrules

# For Python projects
cp ~/dotfiles/prompts/python/AGENTS.md .cursorrules

# For Go projects
cp ~/dotfiles/prompts/golang/AGENTS.md .cursorrules
```

The AGENTS.md files are more comprehensive and match our actual tech stacks:
- **TypeScript**: Bun + SvelteKit 2 + Svelte 5 + Tailwind v4 + Biome
- **Python**: UV + FastAPI + Pydantic v2 + Ruff
- **Golang**: Go 1.22+ stdlib + sqlc

## Why Not Maintain Separate Cursor Rules?

1. **Single source of truth**: AGENTS.md works with Claude Code, Cursor, Gemini, and ChatGPT
2. **Always up to date**: Recipe files are actively maintained
3. **Stack-specific**: Each recipe has patterns for its specific tech stack

## Quick Reference

For project setup, see `~/dotfiles/prompts/README.md` or run:

```bash
# New project
~/dotfiles/prompts/init.sh typescript my-app

# Existing project
~/dotfiles/prompts/seed.sh typescript /path/to/project
```

---

**Note**: The original CursorRules.md content has been archived. The prompts/AGENTS.md approach is preferred.
