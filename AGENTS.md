# Dotfiles Repository

Follow `ai/agents/shared/rules.md` — the universal agent kernel, deployed verbatim to every vendor — plus any project-specific rules below.

**The Engineering Map** ([`ENGINEERING.md`](ENGINEERING.md)) is the single source of truth for how this repo builds: the doctrine (kernel **K1–K8** + 12 principles **P1–P12**), how it's enforced (the gates **G1–G14**), where it fires (the defense-in-depth layers **L0–L5**), and the lenses you reach for — nested in one screen, with a symptom→rite routing table. When the owner says **"the Canon,"** he means *that whole map*; the word is a spoken handle, not a structure. New patterns earn their place by tracing to a principle or gate **by ID**; new beliefs earn theirs by naming the gate that will enforce them.

This is a personal dotfiles and development environment configuration repo. It bootstraps a Mac to a curated developer experience: machine setup scripts, editor configs, and the agentic-coding tooling (rules, skills, MCP) we deploy across vendors.

## What This Repo Contains

- `macos/` -- Homebrew packages, macOS system preferences, bootstrap scripts
- `editors/cursor/` -- Cursor editor settings and extensions
- `editors/obsidian/` -- Obsidian vault settings, community plugins, plugin configs
- `ai/agents/claude/` -- Claude Code plugins, MCP servers, hooks, universal rule deployment
- `ai/agents/cursor/` -- Cursor MCP servers, rules, hooks, universal rule deployment
- `ai/agents/shared/` -- Shared agentic config: `rules.md` (the universal agent kernel deployed to every vendor), MCP servers, ignore patterns
- `ai/skills/` -- Canonical skill source (universal). Deployed to each vendor's user-level dir at setup time via the public `npx skills` CLI (`vercel-labs/skills`) which copies real files into `~/.claude/skills/`, `~/.agents/skills/` (Codex), etc. No per-vendor mirror dirs in this repo.
- `ai/subagents/` -- Canonical subagent source (single `.md` files). Deployed via a small `cp` loop since `npx skills` only handles SKILL.md-shaped skills.
- `ai/prompts/` -- System-prompt artifacts (advisor/detailed system prompts, `gemini-chunks/`) loaded by `dotfiles agent web copy`
- `ai/audits/` -- Audit prompts run by scheduled bot-audits on a cadence (also usable ad hoc)
- `ai/.agents/` -- Permission profiles (`generate-permissions.sh`, `safe-commands.yaml`); ephemeral plans/research gitignored under subdirs
- `ai/artifacts/` -- **gitignored**, created on demand for ephemeral agent working files (durable output goes in `docs/`)

## This Repo

This is a dotfiles and dev environment repo, not a typical application. Key differences:

- **Two layers, two languages.** The bootstrap/machine-setup layer is **Bash** (`install.sh`, `macos/`, the guard hooks) — scripts use `set -euo pipefail` (`set -eo pipefail` when arrays may be unset), except the resilient bootstrappers (`install.sh`, `bin/dotfiles`) that tolerate failures by design. The **agentic-fleet tooling and the `dotfiles` CLI are Python/Typer** under `cli/` — ~26k LOC, heavily gated (ruff, pyright strict, complexity ≤9, coverage, the ratchet). Most feature work lands here, not in Bash.
- **Print system (Bash)** — use functions from `macos/print_utils.sh` (print_success, print_info, print_warn, print_action, print_step, print_skip, etc.). Never use raw `echo` or bare `printf` for user-facing output. The Python CLI uses `dotfiles.console` instead.
- **Idempotent** — every script/command must be safe to re-run. Check before creating, skip if present, don't error on existing state.
- **Adding a CLI feature** — `bin/dotfiles` is a thin dispatcher that `exec`s the Python CLI; new commands are **Typer subcommands under `cli/src/dotfiles/cmd/`**, not bash in `bin/dotfiles` or standalone scripts.

## Key Invariants

- `macos/packages.toml` is the source of truth for what's installed. `bin/dotfiles doctor` and `dotfiles brew stale` must stay in sync with these lists.
- `README.md` documents user-facing features. When adding/removing/renaming commands, packages, or config, update the README in the same commit.
- `ai/agents/shared/rules.md` is the canonical universal rule kernel — one hand-authored doc deployed verbatim to every vendor by `dotfiles agent setup` (Cursor gets a frontmatter wrapper). No baking, no per-rule symlinks. Language/framework opinions are NOT pushed as rules — they live as reference in `docs/stacks/`.
- `ai/skills/` is the canonical skill library. Edit there; `dotfiles agent setup` deploys to each vendor via the public `npx skills` CLI (claude-code) and a small `cp` loop for subagents (codex). No per-vendor mirror dirs in this repo. Validate with `dotfiles agent lint`.
- **Decisions and curated memory live in this repo, under version control — not in any coding tool's private memory.** Record durable decisions in curated `docs/` guides; `docs/adr/` is gitignored scratch space if tools recreate it. Permission profiles and safe-command tiers live in `ai/.agents/`. Unless something must stay private, prefer the repo so the curated memory is owned by the project, reviewable, and portable across tools.

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
- `ENGINEERING.md` (repo root) -- **the Engineering Map**: the one-screen nesting of doctrine → enforcement → layers → tools, with stable IDs (K/P/G/L) and the symptom→rite routing table. Start here. ("the Canon" is the spoken alias for this whole map.)
- `docs/knowledge/how-we-build.md` -- the **visual defense-in-depth map**: every gate/rite by layer (author-time → pre-commit → pre-push → CI → scheduled → convergence), deterministic vs stochastic, the test pyramid, how to work within it
- `docs/engineering-philosophy.md` -- the 12 universal code-health principles (Canon, article II)
- `docs/knowledge/engineering-gates.md` -- how each principle is enforced mechanically (the toolbelt doctrine)
- `docs/knowledge/code-health-portfolio.md` -- the code-health lenses + entry-point map (the Catechism); `docs/health/` holds per-scope state + the independent `ASSESSMENT.md`
- `docs/stacks/` -- technology taste by language/framework (pick/avoid, idioms, patterns), plus `services.md`, `infrastructure.md`, `python/ml.md`
- `docs/knowledge/` -- cross-cutting practice: `ai-tools.md`, `token-efficiency.md`, `browser-tooling.md`, `customer-discovery.md`, `project-memory.md`, prompting guides
- `docs/pi-power-setup.md` -- Pi agent power setup (mitsupi, safe-git, oh-my-pi vs base Pi)
