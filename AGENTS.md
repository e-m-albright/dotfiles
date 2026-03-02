# Dotfiles Repository

Read all `.cursor/rules/*.mdc` files for process, safety, and coding conventions.

This is a personal dotfiles and development environment configuration repo. It manages machine setup scripts, editor configs, prompt recipes, and Cursor rules.

## What This Repo Contains

- `macos/` -- Homebrew packages, macOS system preferences, bootstrap scripts
- `editors/cursor/` -- Cursor/VS Code settings, extensions, MCP config
- `prompts/` -- Scaffolding recipes and AGENTS.md templates for new projects
- `.cursor/rules/` -- Cursor IDE rules (symlinked to projects, also read by Claude/Gemini via this file)

## Working in This Repo

- Scripts must be idempotent -- safe to re-run without side effects.
- Preserve `set -eo pipefail` in shell scripts.
- Check for existing state before installing anything.
- Never embed secrets in any file.
- Guard OS-specific commands behind platform checks.
- Quote all variable expansions (`"$var"` not `$var`).

## Reference Docs

- `prompts/shared/AI_TOOLS.md` -- AI frameworks, evals, coding assistants
- `prompts/shared/SERVICES.md` -- Cloud services reference
- `prompts/shared/INFRASTRUCTURE.md` -- Docker, Pulumi, observability
- `prompts/shared/CUSTOMER_DISCOVERY.md` -- Customer interview methodology
- `prompts/shared/STYLE_PRINCIPLES.md` -- Universal code style
- `prompts/shared/PROJECT_MEMORY.md` -- Decision organization system
