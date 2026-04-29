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
- `.ai/prompts/` -- Reusable, versioned audit/review prompts (universal, language-agnostic templates)
- `.ai/skills/` -- Universal skill definitions (graded `code-quality-audit`, others)
- `.ai/artifacts/` -- **gitignored** ephemeral working files (research notes, audit raw outputs, session logs)
- `prompts/` -- Scaffolding recipes, templates, and reference guides

## This Repo

This is a dotfiles and dev environment repo, not a typical application. Key differences:

- **Primary language is Bash** — all scripts use `set -euo pipefail` (or `set -eo pipefail` when arrays may be unset)
- **Print system** — use functions from `macos/print_utils.sh` (print_success, print_info, print_warn, print_action, print_step, print_skip, etc.). Never use raw `echo` or bare `printf` for user-facing output.
- **Idempotent** — every script must be safe to re-run. Check before creating, skip if present, don't error on existing state.
- **The `dotfiles` command** (`bin/dotfiles`) is the user-facing CLI. New features should be subcommands here, not standalone scripts.

## Key Invariants

- `brew.sh` package lists are the source of truth for what's installed. `bin/dotfiles doctor` and `bin/dotfiles stale` must stay in sync with these lists.
- `README.md` documents user-facing features. When adding/removing/renaming commands, packages, or config, update the README in the same commit.
- `.ai/rules/` is the canonical rule library. Universal process rules (`process/*.mdc`) deploy to user-level via setup scripts (symlinked). Recipe rules are copied into projects by `scaffold.sh`.
- `prompts/guides/skills/*.md` are implementation references that complement `.ai/rules/`. They should stay consistent with each other.
- `agents/shared/tool-targets.json` is the tool discovery registry. Adding a new AI tool means adding a JSON entry, not writing code.

## Working in This Repo

- Scripts must be idempotent -- safe to re-run without side effects.
- Preserve `set -eo pipefail` in shell scripts.
- Check for existing state before installing anything.
- Never embed secrets in any file.
- Guard OS-specific commands behind platform checks.
- Quote all variable expansions (`"$var"` not `$var`).

## Command Style (Reduce Permission Prompts)

- **Prefer dedicated tools** over Bash: use Read instead of `cat`, Glob instead of `find`, Grep instead of `grep`/`rg`, Edit instead of `sed`.
- **Prefer single commands** over chained `&&` / `||` — each command in a chain triggers separate permission checks.
- **Avoid `$(...)` substitution in Bash** when the same result can be achieved with a dedicated tool or a simpler command.
- **Use heredocs for multi-line content** via the Write tool, not `echo`/`cat` redirection in Bash.

## Common Pitfalls

- `printf "%s"` does not interpret escape codes — use `%b` when the argument contains `\033[` color sequences (see `print_todo`).
- `ssh -T git@github.com` exits with code 1 even on success — capture output with `|| true` before grepping.
- `set -eo pipefail` kills pipelines where the left side exits non-zero — capture to a variable first if needed.

## Reference Docs

- `prompts/guides/ai-tools.md` -- AI frameworks, evals, coding assistants
- `prompts/guides/services.md` -- Cloud services reference
- `prompts/guides/infrastructure.md` -- Docker, Pulumi, observability
- `prompts/guides/customer-discovery.md` -- Customer interview methodology
- `prompts/guides/project-memory.md` -- Decision organization system
- `prompts/guides/ml-python.md` -- Python ML/data science patterns
- `prompts/guides/token-efficiency.md` -- LLM token efficiency, task decomposition, model routing
- `prompts/guides/browser-tooling.md` -- Tiered browser/UI tools (Playwright tests, agent-browser, pinchtab, Playwright MCP, Chrome DevTools MCP, Stagehand)
- `docs/engineering-philosophy.md` -- 12 universal principles for code health (compiler-first, type the domain, single source of truth, etc.)
- `docs/specs/2026-04-28-ophira-backport.md` -- Active backport plan: which Ophira patterns are landing here, in what order
