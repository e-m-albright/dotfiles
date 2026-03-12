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
git clone https://github.com/e-m-albright/dotfiles ~/dotfiles
~/dotfiles/install.sh

# 3. Re-run anytime (idempotent)
dotfiles install
```

**What you get:**
- Shell: Zsh + Oh My Zsh + custom theme
- Runtimes: Go, Rust, Bun, Node.js (fnm), Python (uv)
- Editor: Cursor + MCP servers
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
```

Safe to run multiple times — only adds missing pieces. AGENTS.md is generated once, then project-owned (use `--force` to regenerate).

This adds cross-vendor AI rules — lightweight scaffolding that guides AI agents:

```
my-project/
├── AGENTS.md              # ~30 lines: pointers + project context (project-owned)
├── .ai/rules/*.mdc        # AI rules (universal + recipe-specific, all copied)
├── .cursor/rules/*.mdc    # Cursor symlinks → .ai/rules/ (auto-generated)
├── .agents/               # Working files, gitignored (plans, research, sessions)
└── .agents/decisions/     # Architecture Decision Records (versioned)
```

**How rules are deployed:**
- **Universal rules** (process, style) are copied — re-run with `--force` to update from dotfiles
- **Recipe rules** (language, framework, stack) are copied — project can customize
- **Cursor symlinks** are auto-generated relative links to `.ai/rules/`
- Only rules relevant to the recipe are deployed, not the entire library

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

### Runtimes

| Runtime | Manager | Notes |
|---------|---------|-------|
| **Node.js** | fnm | LTS version, auto-switches per project |
| **Bun** | direct | Preferred JS runtime (faster than Node) |
| **Python** | uv | Python 3.14, fast package management |
| **Go** | brew | With gopls, delve, air, sqlc, goose, templ, staticcheck |
| **Rust** | rustup | Via official installer (not Homebrew) |

### Editors

- **Cursor**: Primary editor (AI-native, VS Code compatible, MCP servers configured)
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
| **Core** | git, git-lfs, delta (diffs), gh (GitHub CLI), jq, yq, wget |
| **System** | htop, iftop, nmap, dockutil, terminal-notifier |
| **Dev** | just (task runner), lefthook (git hooks), shellcheck (shell linting), hyperfine (benchmarks), atlas (migrations), duckdb |

### AI Tools

| Tool | Purpose |
|------|---------|
| **Claude Code** | Agentic coding assistant (CLI) with plugins, hooks, MCP servers |
| **Claude Desktop** | Claude macOS app |
| **Cursor** | AI-native editor with MCP servers |

### External Connections

Services we integrate with, and how. Prefer CLIs (simplest) > MCPs (cross-tool) > plugins (tool-specific).

| Service | Method | Claude Code | Cursor | Notes |
|---------|--------|:-----------:|:------:|-------|
| **GitHub** | CLI (`gh`) | yes | yes | CLI only — no MCP needed |
| **Linear** | MCP (`mcp-remote`) | yes | yes | Issue tracking |
| **Context7** | MCP (`@upstash/context7-mcp`) | plugin | yes | Up-to-date library docs |
| **Granola** | MCP (`granola-mcp` via `uvx`) | yes | — | Meeting notes (reads local cache, no API key) |
| **Notion** | Plugin | yes | — | Claude Code / Claude Desktop only |
| **Gmail** | claude.ai cloud MCP | yes | — | Claude Code only (not reproducible in config) |
| **Google Calendar** | claude.ai cloud MCP | yes | — | Claude Code only (not reproducible in config) |

**Considered** (not yet enabled — add to `claude/mcp.json` when needed):

| Service | Method | Why consider | Status |
|---------|--------|-------------|--------|
| **Slack** | MCP (`mcp-remote`) | Team comms — search channels, post messages, triage threads | Evaluate |
| **Datadog** | MCP / CLI (`datadog-ci`) | APM, logs, dashboards, incident context | Evaluate |
| **Sentry** | MCP / CLI (`sentry-cli`) | Error tracking, issue triage, release management | Evaluate |
| **Dagster** | Plugin / MCP | Data pipeline orchestration & observability | Evaluate |

MCP config: `claude/mcp.json` (Claude Code + Desktop) and `editors/cursor/mcp.json` (Cursor).

### Claude Code

Setup is automated via `dotfiles claude-setup` (also runs during install):

- **Global instructions**: `~/.claude/CLAUDE.md` installed from `claude/global-claude.md` (process guardrails, command style, project file discovery)
- **Plugins**: 19 plugins (LSP, workflows, tooling, quality, integrations)
- **Hooks**: Format-on-save (biome/ruff/rustfmt/gofmt), terminal notifications on completion
- **MCP servers**: Linear, Granola, Notion (standalone); Context7, Playwright (via plugins)
- **Cloud MCPs**: Gmail, Google Calendar (configured via claude.ai, not in dotfiles)
- **Preferences**: Voice mode, terminal bell, acceptEdits mode
- **Desktop**: MCP servers + preferences (cowork, sidebar, web search)

See `claude/` for all configuration files.

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
dotfiles doctor              # Check all tools are installed correctly
dotfiles update              # Update OS, Homebrew, and Node.js LTS
dotfiles clean               # Clear Homebrew caches
dotfiles brew                # Re-run Homebrew setup
dotfiles dock                # Reset Dock layout
dotfiles scaffold            # Scaffold a project with AI rules
dotfiles stale               # Find disabled packages still installed
dotfiles profile-shell       # Profile shell startup time
dotfiles claude-setup        # Configure Claude Code + Desktop (global config)
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
├── editors/                # Cursor settings + MCP servers + Obsidian vault configs
├── terminal/               # Ghostty config
├── claude/                 # Claude Code setup (plugins, hooks, MCP servers)
├── macos/                  # Homebrew, Dock, SSH, print utilities
├── .ai/rules/              # Cross-vendor AI rules (canonical source)
│   ├── process/            # Universal: safety, style, workflow
│   ├── languages/          # Language ergonomics: TS, Python, Go, Rust
│   ├── frameworks/         # Framework patterns: SvelteKit, Astro, FastAPI, etc.
│   └── tooling/            # Stack decisions: Pick/Avoid tables, services
└── prompts/                # Project scaffolding
    ├── scaffold.sh         # Deploy rules + templates to projects
    ├── guides/             # Reference docs (not deployed to projects)
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
