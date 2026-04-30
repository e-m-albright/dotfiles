# Dotfiles

Opinionated Mac setup + project scaffolding for fast, maintainable development.

**Two things happen here:**

1. **Machine setup** — Run `install.sh` and get a fully configured dev environment
2. **Project scaffolding** — Seed new or existing projects with cross-vendor AI rules

---

## Quick Start

### Fresh Mac Setup

```bash
# 1. Install Xcode CLI tools
xcode-select --install

# 2. Clone and run
git clone https://github.com/<your-username>/dotfiles ~/dotfiles
~/dotfiles/install.sh

# 3. Re-run anytime (idempotent)
dotfiles install
```

**What you get:**
- Shell: Zsh + Oh My Zsh + custom theme
- Runtimes: Go, Rust, Bun, Node.js (fnm), Python (uv)
- Editor: Cursor (AI-native, shared MCP servers)
- Terminal: Ghostty (GPU-accelerated, desktop notifications)
- CLI: Git, gh, just, jq, delta, hyperfine, and more
- AI: Claude Code (with plugins, hooks, MCP servers), Claude Desktop

The installer is idempotent — safe to re-run anytime.

---

## Project Scaffolding

Seed new or existing projects with cross-vendor AI rules that work with Claude Code, Cursor, and Gemini CLI.

### Usage

```bash
# Create new projects
dotfiles scaffold typescript my-app           # SvelteKit (default)
dotfiles scaffold typescript astro my-blog    # Astro
dotfiles scaffold python my-api               # FastAPI (default)
dotfiles scaffold python cli my-tool          # Typer CLI
dotfiles scaffold golang my-service           # Chi (default)
dotfiles scaffold rust my-tool                # Axum (default)

# Seed existing projects (use . for current directory)
dotfiles scaffold typescript .
dotfiles scaffold python ~/code/my-api

# Force-update rules in an existing project
dotfiles scaffold --force python .

# Add extra tool support (default: claude + cursor)
dotfiles scaffold python my-api --tools copilot,gemini
dotfiles scaffold --tools all python my-api
```

Safe to run multiple times — only adds missing pieces. AGENTS.md is generated once, then project-owned (use `--force` to regenerate).

This adds cross-vendor AI rules — lightweight scaffolding that guides AI agents:

```
my-project/
├── AGENTS.md                  # Universal entry point (project-owned)
├── .ai/
│   ├── rules/*.mdc            # Recipe-specific rules (copied from dotfiles)
│   └── artifacts/             # Working files (gitignored)
│       ├── plans/
│       ├── research/
│       ├── decisions/         # ADRs (versioned)
│       └── sessions/
└── .cursor/rules/             # Cursor symlinks → .ai/rules/ (default)
    # Plus --tools extras: .github/instructions/, .gemini/rules/, GEMINI.md→, CODEX.md→ (symlinks to AGENTS.md)
```

**How rules are deployed:**
- **Universal rules** (process, safety, style) are deployed at the **user level** by `dotfiles agent-setup` / `dotfiles install` — symlinked to dotfiles so they're always current
- **Recipe rules** (language, framework, stack) are **copied into projects** — project can customize
- **Tool symlinks** are auto-generated from a registry (`agents/shared/tool-targets.json`)
- Default tools: claude + cursor. Use `--tools copilot,gemini` or `--tools all` for more.

**Multi-tool rule discovery** — `.ai/rules/` is the single source of truth. `scaffold.sh` creates tool-specific symlinks so each AI tool discovers the same rules in its native directory:

| Tool | Discovery | Directory |
|------|-----------|-----------|
| Claude Code | CLAUDE.md → AGENTS.md | (direct) |
| Cursor | Symlinks | .cursor/rules/ |
| Codex CLI | CODEX.md → AGENTS.md | (direct, also reads AGENTS.md natively) |
| Jules | AGENTS.md | (cloud-only, reads from GitHub repo directly) |
| GitHub Copilot | Symlinks | .github/instructions/ |
| Gemini CLI | GEMINI.md → AGENTS.md + symlinks | .gemini/rules/ |

### Available Recipes

| Recipe | App Type | Stack | Use Case |
|--------|----------|-------|----------|
| `typescript` | `svelte` (default) | Bun + SvelteKit 2 + Svelte 5 | Full-stack apps |
| `typescript` | `astro` | Bun + Astro | Content sites, blogs |
| `python` | `fastapi` (default) | UV + FastAPI + SQLAlchemy | APIs, AI services |
| `python` | `cli` | UV + Typer + Rich | CLI tools, scripts |
| `golang` | `chi` (default) | Go 1.25+ Chi router + sqlc | APIs, services |
| `rust` | `axum` (default) | Tokio + Axum + SQLx | APIs, services |
| `rust` | `tauri` | Tauri 2 + SvelteKit | Desktop apps |

---

## What's Installed

### Shell & Terminal

- **Zsh + Oh My Zsh**: Custom two-line prompt with git status, venv indicator, error-aware prompt character
- **Ghostty**: GPU-accelerated terminal with desktop notifications
- **Rectangle**: Window management
- **Shell aliases**: `cc` (Claude Code with profiles), `ccr` (AI code review), `cca` (address PR feedback)

### Runtimes

| Runtime | Manager | Notes |
|---------|---------|-------|
| **Node.js** | fnm | LTS version, auto-switches per project |
| **Bun** | direct | Preferred JS runtime (faster than Node) |
| **Python** | uv | Python 3.14, fast package management |
| **Go** | brew | With gopls, delve, air, sqlc, goose, templ, staticcheck |
| **Rust** | rustup | Via official installer (not Homebrew) |

### Editors

- **Cursor**: Primary editor (AI-native, VS Code compatible, shared MCP servers, hooks, skills, agents)
- **Obsidian**: Knowledge base — vault configs + community plugins managed via symlinks

  | Plugin | Purpose |
  |--------|---------|
  | **Spaced Repetition** | Flashcards in notes (`question::answer`), SM-2 scheduling |
  | **Dataview** | Query notes like a database (inline JS/DQL) |
  | **Templater** | Advanced templates with JS expressions |
  | **Calendar** | Visual calendar sidebar linked to daily notes |
  | **Natural Language Dates** | Type `@tomorrow` → date link |
  | **Linter** | Auto-format markdown on save |

### CLI Tools

| Category | Tools |
|----------|-------|
| **Core** | git, git-lfs, delta (diffs), gh (GitHub CLI), jq, yq, wget, fd, ripgrep, fzf, zoxide, micro (editor), yazi (file manager) + preview helpers (poppler, resvg, imagemagick, sevenzip) |
| **System** | htop, iftop, nmap, dockutil, terminal-notifier |
| **Dev** | just (task runner), lefthook (git hooks), shellcheck (shell linting), hyperfine (benchmarks), atlas (migrations), duckdb, infisical (secrets) |

### Daily Drivers — Power User Tips

Most of the CLI tools above have a steep-ish learning curve that pays for itself in days. This is the minimum set of shortcuts worth memorising.

#### fzf keybindings (shell-wide)

Loaded by `.zshrc` via `source <(fzf --zsh)` — active everywhere.

| Key | Action |
|-----|--------|
| `Ctrl-T` | Fuzzy-pick file(s), paste path(s) at cursor. E.g. `git add <Ctrl-T>`, `cursor <Ctrl-T>` |
| `Ctrl-R` | Fuzzy-search shell history. Replaces the default reverse-i-search. |
| `Alt-C`  | Fuzzy-cd into any subdirectory of cwd |
| `**<Tab>` | Trigger fzf anywhere. `ssh **<Tab>` (hosts), `kill -9 **<Tab>` (PIDs), `git co **<Tab>` (branches) |
| `Tab` on a path | Path completion via fzf |

Inside any fzf prompt: `'foo` = exact match, `!bar` = exclude, `^prefix` / `suffix$` = anchor.

#### zoxide — smart `cd`

Defines `z` and `zi` (replaces the oh-my-zsh `z` plugin). Learns from your `cd` history; a path has to be visited once before `z` will jump to it.

| Command | Action |
|---------|--------|
| `z <word>` | Jump to best-ranked dir matching `word` |
| `z foo bar` | Multi-keyword — dir must match both. `z dot shell` → `~/dotfiles/shell` |
| `zi` | Interactive picker over all tracked dirs (uses fzf) |
| `z -` | Previous directory |

#### fd — fast file finder (replaces `find`)

Respects `.gitignore` by default.

| Command | Purpose |
|---------|---------|
| `fd pattern` | Find files matching regex on name |
| `fd -e md` | Filter by extension |
| `fd -H pattern` | Include hidden files |
| `fd -t d pattern` | Directories only (`-t f` = files) |
| `fd pattern -x cmd {}` | Run `cmd` on each match (replaces `find -exec`) |

#### ripgrep (`rg`) — fast content search

Respects `.gitignore` by default. **`grep` will feel broken after you learn this.**

| Command | Purpose |
|---------|---------|
| `rg pattern` | Search file contents recursively from cwd |
| `rg -l pattern` | Just filenames that match |
| `rg -C 3 pattern` | 3 lines of context before + after |
| `rg -t py pattern` | Type-filtered (common: `py`, `go`, `rust`, `md`, `ts`) |
| `rg -g '*.toml' pattern` | Glob-filtered |
| `rg --files` | List all non-ignored files (faster than `fd` for "everything") |

#### yazi — terminal file manager

Launch with `yz` (wrapper function — see below). Navigation is vim-keyed.

| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Navigate (←↓↑→) |
| `space` | Toggle-select (multi-select by holding + repeating) |
| `enter` / `o` | Open with default app |
| `y` / `x` / `p` | Copy / cut / paste |
| `d` / `D` | Trash / permanent-delete |
| `a` / `r` | Create file or dir / rename |
| `/` | Search in current dir |
| `f` / `F` | Find-by-name (fd) / find-in-files (rg) |
| `z` | Jump to directory via zoxide |
| `i` / `I` | Scroll preview pane up/down |
| `t` / `1`–`9` | New tab / switch tab |
| `g` / `G` | Top / bottom of list |
| `q` | Quit (shell follows via the `yz` wrapper) |

Preview pane auto-uses the installed companions: `poppler` (PDFs), `resvg` (SVGs), `imagemagick` (HEIC/PSD/TIFF), `sevenzip` (peek inside archives).

**Key yazi tip:** `yz` is defined as a shell function (in `.zshrc`), not a plain alias — so when you quit yazi, your shell `cd`s to wherever you ended up. This turns yazi from a viewer into a navigator.

#### High-value combos

| Combo | Effect |
|-------|--------|
| `cursor $(fd -t f \| fzf)` | Fuzzy-pick a file and open in Cursor |
| `cd $(zoxide query -l \| fzf)` | Equivalent to `zi`, useful when scripting |
| `rg -l pattern \| xargs cursor` | Open every matching file in Cursor |
| `fd -e py -x wc -l {}` | Run a command on every matched file |
| `gh pr list \| fzf` | Fuzzy-pick a PR (any gh-listed thing, really) |

### AI Tools

| Tool | Provider | Status | Purpose |
|------|----------|--------|---------|
| **Claude Code** | Anthropic | active | Agentic coding assistant (CLI) with plugins, hooks, MCP servers |
| **Claude Desktop** | Anthropic | active | Claude macOS app |
| **Cursor** | Cursor | active | AI-native editor with shared MCP servers, hooks, skills, agents |
| **Codex CLI** | OpenAI | active | Terminal coding agent (open-source, o4-mini default) |
| **Copilot CLI** | GitHub | disabled | Terminal coding agent (fleet mode, cloud delegation) |
| **Codex Desktop** | OpenAI | disabled | macOS app for parallel coding agents |
| **GWS CLI** | Google | active | Google Workspace CLI (Drive, Gmail, Calendar, Sheets, Admin) |
| **Gemini CLI** | Google | disabled | Terminal coding agent (Gemini 2.5 Pro, free tier) |
| **Antigravity** | Google | disabled | AI-native IDE (dual Editor/Manager view) |

**Cursor extensions** (managed in `editors/extensions.sh`):

| Extension | Status | Notes |
|-----------|--------|-------|
| `anthropic.claude-code` | active | Claude Code companion inside Cursor |
| `github.copilot` | disabled | Conflicts with Cursor built-in AI |
| `google.gemini-code-assist` | disabled | Gemini Code Assist for IDE |
| `openai.codex` | disabled | Codex IDE extension |

See `prompts/guides/ai-tools.md` for the full landscape and investigation notes.

### Codex CLI

Setup is automated via `dotfiles agent-setup` (also runs during install):

- **Global instructions**: `~/.codex/AGENTS.md` deployed from shared rules
- **Config**: `~/.codex/config.toml` with MCP servers and `project_doc_fallback_filenames = ["CODEX.md"]`
- **Hooks**: Format-on-save (reuses Claude's hook), sensitive file guard, terminal notifications
- **Skills**: `dotfiles-doctor`, `pr-summary`, `git-worktree-manager`, `dep-audit`, `brew-reconcile`, `migration-writer`
- **Agents**: `shellcheck-reviewer`
- **MCP servers**: From shared source (`agents/shared/mcp-servers.json`) — targets "codex" or "claude"

See `agents/codex/` for all configuration files.

### External Connections

Services we integrate with, and how. Prefer CLIs (simplest) > MCPs (cross-tool) > plugins (tool-specific).

| Service | Method | Claude Code | Cursor | Codex | Notes |
|---------|--------|:-----------:|:------:|:-----:|-------|
| **GitHub** | CLI (`gh`) + MCP | yes | yes | yes | CLI + MCP server (`gh mcp-server`) |
| **Linear** | MCP (`mcp-remote`) | yes | yes | yes | Issue tracking |
| **Context7** | MCP (`@upstash/context7-mcp`) | plugin | yes | — | Up-to-date library docs |
| **Neon** | ~~MCP~~ (disabled) | — | — | — | Neon Postgres; revisit when actively using Neon projects |
| **Granola** | MCP (`granola-mcp` via `uvx`) | yes | — | — | Meeting notes (reads local cache, no API key) |
| **Notion** | MCP | yes | yes | yes | Via shared MCP servers |
| **Playwright** | MCP (`@playwright/mcp`) | yes | yes | yes | Tier 3a — drive a real page, screenshot, click, network. WebRTC-capable. |
| **Chrome DevTools** | MCP (`chrome-devtools-mcp`) | yes | yes | yes | Tier 4 — Chrome-only forensics: network, console, perf traces |
| **agent-browser** | CLI (`agent-browser`) | yes | yes | yes | Tier 2 — token-cheap (~200-400/page) "look at this page" CLI. No MCP overhead. |
| **pinchtab** | CLI (`pinchtab`) | yes | yes | yes | Tier 2 — accessibility-tree extraction (~800 tokens/page). HTTP API. |
| **Stagehand** | per-project SDK (`@browserbasehq/stagehand`) | yes | yes | yes | Tier 5 — natural-language test framework for long agentic flows. Install per-project. |
| **Gmail** | claude.ai cloud MCP | yes | — | — | Claude Code only (not reproducible in config) |
| **Google Calendar** | claude.ai cloud MCP | yes | — | — | Claude Code only (not reproducible in config) |

**Considered** (not yet enabled — add to `agents/shared/mcp-servers.json` when needed):

| Service | Method | Why consider | Status |
|---------|--------|-------------|--------|
| **Slack** | MCP (`mcp-remote`) | Team comms — search channels, post messages, triage threads | Evaluate |
| **Datadog** | MCP / CLI (`datadog-ci`) | APM, logs, dashboards, incident context | Evaluate |
| **Sentry** | MCP / CLI (`sentry-cli`) | Error tracking, issue triage, release management | Evaluate |
| **Dagster** | Plugin / MCP | Data pipeline orchestration & observability | Evaluate |

MCP config: `agents/shared/mcp-servers.json` (shared source), deployed to Claude Code and Cursor by their respective setup scripts.

### Claude Code

Setup is automated via `dotfiles agent-setup` (also runs during install):

- **Global instructions**: `~/.claude/CLAUDE.md` installed from `agents/claude/global-claude.md` (process guardrails, command style, project file discovery)
- **Universal rules**: `~/.claude/rules/*.mdc` symlinked from `.ai/rules/process/` (always current with dotfiles)
- **Plugins**: 19 plugins (LSP, workflows, tooling, quality, integrations)
- **Hooks**: Format-on-save (biome/ruff/rustfmt/gofmt/shellcheck), sensitive file guard, terminal notifications on completion
- **Skills**: `scaffold-project`, `dotfiles-doctor`
- **Agents**: `shellcheck-reviewer`
- **MCP servers**: From shared source (`agents/shared/mcp-servers.json`) — GitHub, Linear, Granola, Notion, Playwright, Chrome DevTools (standalone); Context7 (via plugin)
- **Browser-tool tiers**: See `prompts/guides/browser-tooling.md` — when to reach for Playwright tests (Tier 1), agent-browser/pinchtab CLIs (Tier 2), Playwright/Chrome DevTools MCPs (Tier 3-4), or Stagehand (Tier 5)
- **Cloud MCPs**: Gmail, Google Calendar (configured via claude.ai, not in dotfiles)
- **Preferences**: Voice mode, terminal bell, acceptEdits mode
- **Desktop**: MCP servers + preferences (cowork, sidebar, web search)

**Shell workflow aliases** (in `.zshrc`):

| Alias | Usage | Description |
|-------|-------|-------------|
| `cc` | `cc [-w] [-a\|-p\|-e] [--chrome]` | Launch Claude Code with worktree + permission profile |
| `ccc` | `ccc -wa`, `ccc --yolo` | Claude Code in Chrome — shorthand for `cc --chrome` |
| `ccr` | `ccr`, `ccr 2277`, `ccr <url>` | AI code review — local uses `/review-pr` (6 agents), PR uses `/code-review` (5 agents + GitHub comments) |
| `cca` | `cca [-c] [-p] [PR]` | Address PR feedback — `-c` replies to comments, `-p` pushes |

See `agents/claude/` for all configuration files.

### Cursor

Setup is automated via `agents/cursor/setup.sh` (also runs during install):

- **MCP servers**: From shared source (`agents/shared/mcp-servers.json`)
- **Editor config**: `editors/cursor/settings.json` + `editors/cursor/keybindings.json` symlinked into Cursor User config
- **Universal rules**: Symlinked from `.ai/rules/process/` (always current with dotfiles)
- **Hooks**: Shared hook definitions deployed from `agents/cursor/hooks/`
- **Skills**: Deployed from `agents/cursor/skills/`
- **Agents**: Deployed from `agents/cursor/agents/`
- **Rules**: Shared rules from `agents/shared/rules.md`
- **Marketplace stack**: See `agents/cursor/PLUGINS.md` for core/work plugin recommendations and install commands (`/add-plugin ...`)

Note: Cursor Marketplace plugin installs and OAuth flows are manual by design (run in Cursor chat/UI). The setup scripts print an explicit checklist so these steps are hard to miss.

See `agents/cursor/` for all configuration files.

---

## Configuration

### Homebrew

Edit `macos/brew.sh` to customize packages. Organized by category with opt-in toggles:

```bash
AI=1 PRODUCTIVITY=1 SOCIAL=0 dotfiles brew
```

### The `dotfiles` Command

```bash
dotfiles help                # Show available commands
dotfiles install             # Re-run full setup (install.sh)
dotfiles doctor              # Check all tools are installed (--fix to repair config)
dotfiles update              # Update OS, Homebrew, runtimes, and dev tools
dotfiles clean               # Clear Homebrew caches
dotfiles brew                # Re-run Homebrew setup
dotfiles dock                # Reset Dock layout
dotfiles scaffold            # Scaffold a project with AI rules
dotfiles stale               # Find disabled packages still installed
dotfiles test                # Run scaffold eval framework (--quick for fast)
dotfiles profile-shell       # Profile shell startup time
dotfiles cursor-plugins      # Print Cursor Marketplace plugin install checklist
dotfiles agents              # Show active agentic setup (Claude Code + Cursor)
dotfiles agent-setup        # Configure Claude + Cursor (--work/--personal, optional --reset-mcp)
dotfiles completions         # Output shell completions
```

Enable tab completion:
```bash
# Add to ~/.zshrc
eval "$(dotfiles completions)"
```

### Git

- `.gitconfig`: Modern defaults (delta, push.autoSetupRemote, rebase on pull)
- `.gitconfig.local`: Your name/email (created on first install, not committed)
- `.gitignore_global`: Common ignores

---

## Directory Structure

```
dotfiles/
├── install.sh              # Main installer (run this)
├── bin/                    # CLI tools (dotfiles command)
├── shell/                  # Zsh config + theme
├── git/                    # Git config + global ignores
├── editors/                # Cursor settings + Obsidian vault configs
├── terminal/               # Ghostty config
├── agents/                 # Agentic tool setup
│   ├── shared/             # Shared config (MCP servers, tool registry, rules, ignore patterns)
│   ├── claude/             # Claude Code setup (plugins, hooks, skills, universal rules)
│   ├── codex/              # Codex CLI setup (config.toml, hooks, skills)
│   └── cursor/             # Cursor plugin (hooks, skills, universal rules)
├── macos/                  # Homebrew, Dock, SSH, print utilities
├── .ai/                    # Cross-vendor AI authoring
│   ├── rules/              #   canonical rule library
│   │   ├── process/        #     Universal: safety, style, workflow, artifact placement
│   │   ├── languages/      #     Language ergonomics: TS, Python, Go, Rust
│   │   ├── frameworks/     #     Framework patterns: SvelteKit, Astro, FastAPI, etc.
│   │   └── tooling/        #     Stack decisions: Pick/Avoid tables, services
│   ├── prompts/            #   Reusable audit/review prompts (versioned)
│   │   └── audits/         #     Universal: god-functions, abstractions, coupling, duplication
│   ├── skills/             #   Canonical skill source — agents/<vendor>/skills/<name> are symlinks here
│   └── artifacts/          #   Ephemeral working files (gitignored)
├── docs/
│   ├── engineering-philosophy.md  # 12 universal principles
│   └── specs/              #   In-flight design specs and plans
└── prompts/                # Project scaffolding
    ├── scaffold.sh         # Deploy rules + templates to projects
    ├── guides/             # Reference docs (not deployed to projects)
    │   └── developer-workflow.md  # How all the tools work together
    └── */templates/        # Starter files per recipe (.gitignore, justfile, etc.)
```

---

## TODO

- [ ] **Evaluate Raycast** — Could replace both Rectangle (window management) and Flycut (clipboard manager) with a single tool. Already commented out in `macos/brew.sh`. Prioritize trying this.

---

## Philosophy

**Machine setup:**
- Idempotent — run anytime, get the same result
- Opinionated but removable — edit `brew.sh` to customize
- Fast — parallel installs, skip what's already there

**Project scaffolding:**
- One pick per category — no "it depends"
- Agent-first — all configs work with Claude, Cursor, Gemini
- Start minimal — add tools when you need them, not before
