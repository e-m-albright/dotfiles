# Dotfiles Repository

Read all `.ai/rules/*.mdc` files for process, safety, and coding conventions.

This is a personal dotfiles and development environment configuration repo. It manages machine setup scripts, editor configs, AI rules, and project scaffolding.

## What This Repo Contains

- `macos/` -- Homebrew packages, macOS system preferences, bootstrap scripts
- `editors/cursor/` -- Cursor editor settings and extensions
- `editors/obsidian/` -- Obsidian vault settings, community plugins, plugin configs
- `agents/claude/` -- Claude Code plugins, MCP servers, hooks, universal rule deployment
- `agents/cursor/` -- Cursor MCP servers, rules, hooks, universal rule deployment
- `agents/shared/` -- Shared agentic config (MCP servers, tool registry, rules, ignore patterns)
- `.ai/rules/` -- Cross-vendor AI rules (process, languages, frameworks, tooling)
- `prompts/` -- Scaffolding recipes, templates, and reference guides (`.ai/artifacts/` in projects)

## Working in This Repo

- Scripts must be idempotent -- safe to re-run without side effects.
- Preserve `set -eo pipefail` in shell scripts.
- Check for existing state before installing anything.
- Never embed secrets in any file.
- Guard OS-specific commands behind platform checks.
- Quote all variable expansions (`"$var"` not `$var`).

## Reference Docs

- `prompts/guides/ai-tools.md` -- AI frameworks, evals, coding assistants
- `prompts/guides/services.md` -- Cloud services reference
- `prompts/guides/infrastructure.md` -- Docker, Pulumi, observability
- `prompts/guides/customer-discovery.md` -- Customer interview methodology
- `prompts/guides/project-memory.md` -- Decision organization system
- `prompts/guides/ml-python.md` -- Python ML/data science patterns
