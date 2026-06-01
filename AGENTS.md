# Dotfiles Repository

Read all `.ai/rules/*.mdc` files for process, safety, and coding conventions.

This is a personal dotfiles and development environment configuration repo. It bootstraps a Mac to a curated developer experience: machine setup scripts, editor configs, and the agentic-coding tooling (rules, skills, MCP) we deploy across vendors.

## What This Repo Contains

- `macos/` -- Homebrew packages, macOS system preferences, bootstrap scripts
- `editors/cursor/` -- Cursor editor settings and extensions
- `editors/obsidian/` -- Obsidian vault settings, community plugins, plugin configs
- `agents/claude/` -- Claude Code plugins, MCP servers, hooks, universal rule deployment
- `agents/cursor/` -- Cursor MCP servers, rules, hooks, universal rule deployment
- `agents/shared/` -- Shared agentic config (MCP servers, tool registry, rules, ignore patterns)
- `.ai/rules/` -- Cross-vendor AI process rules (the universal kernel; language/framework taste lives in `docs/stacks/`)
- `.ai/prompts/` -- Reusable, versioned audit/review prompts (universal, language-agnostic templates)
- `.ai/skills/` -- Canonical skill source (universal). Deployed to each vendor's user-level dir at setup time via the public `npx skills` CLI (`vercel-labs/skills`) which copies real files into `~/.claude/skills/`, `~/.agents/skills/` (Codex), etc. No per-vendor mirror dirs in this repo.
- `.ai/agents/` -- Canonical subagent source (single `.md` files). Deployed via small `cp` loops in each vendor's `setup.sh` since `npx skills` only handles SKILL.md-shaped skills.
- `.ai/artifacts/` -- **gitignored** ephemeral working files (research notes, audit raw outputs, session logs)
- `prompts/` -- Prompt-construction assets (system prompts, advisor personas) + the `scaffolds/agent-rules-sync` fragment used by `dotfiles agent migrate-rules-sync`

## This Repo

This is a dotfiles and dev environment repo, not a typical application. Key differences:

- **Primary language is Bash** — all scripts use `set -euo pipefail` (or `set -eo pipefail` when arrays may be unset)
- **Print system** — use functions from `macos/print_utils.sh` (print_success, print_info, print_warn, print_action, print_step, print_skip, etc.). Never use raw `echo` or bare `printf` for user-facing output.
- **Idempotent** — every script must be safe to re-run. Check before creating, skip if present, don't error on existing state.
- **The `dotfiles` command** (`bin/dotfiles`) is the user-facing CLI. New features should be subcommands here, not standalone scripts.

## Key Invariants

- `macos/packages.toml` is the source of truth for what's installed. `bin/dotfiles doctor` and `dotfiles brew stale` must stay in sync with these lists.
- `README.md` documents user-facing features. When adding/removing/renaming commands, packages, or config, update the README in the same commit.
- `.ai/rules/process/` is the canonical universal rule kernel, deployed globally to every vendor by `dotfiles agent setup`. Language/framework opinions are NOT pushed as rules — they live as reference in `docs/stacks/`.
- `.ai/skills/` is the canonical skill library. Edit there; `dotfiles agent setup` deploys to each vendor via the public `npx skills` CLI (claude-code) and a small `cp` loop for subagents (codex). No per-vendor mirror dirs in this repo. Validate with `dotfiles validate-skills`.
- **Decisions and curated memory live in this repo, under version control — not in any coding tool's private memory.** Record decisions as ADRs in `docs/adr/` (numbered, committed); keep curated tool/stack notes in `docs/`. Unless something must stay private, prefer the repo so the curated memory is owned by the project, reviewable, and portable across tools.

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

The curated knowledge base lives in `docs/` (see `docs/README.md`):
- `docs/stacks/` -- technology taste by language/framework (pick/avoid, idioms, patterns), plus `services.md`, `infrastructure.md`, `python/ml.md`
- `docs/knowledge/` -- cross-cutting practice: `ai-tools.md`, `token-efficiency.md`, `browser-tooling.md`, `customer-discovery.md`, `project-memory.md`, prompting guides
- `docs/engineering-philosophy.md` -- 12 universal code-health principles; `docs/adr/` -- numbered decisions
- `docs/pi-power-setup.md` -- Pi agent power setup (mitsupi, safe-git, oh-my-pi vs base Pi)
