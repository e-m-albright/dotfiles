# Dotfiles

Opinionated Mac setup + project scaffolding for fast, maintainable development.

**Two things happen here:**

1. **Machine setup** — Run `install.sh` and get a fully configured dev environment
2. **Project scaffolding** — Seed new or existing projects with thoughtful structure

---

## Quick Start

### Fresh Mac Setup

```bash
# 1. Install Xcode CLI tools
xcode-select --install

# 2. Clone and run
git clone https://github.com/e-m-albright/dotfiles ~/dotfiles
~/dotfiles/install.sh
```

**What you get:**
- Shell: Zsh + Oh My Zsh + custom theme
- Runtimes: Bun, Node.js (fnm), Python (uv)
- Editor: Cursor (with VS Code as fallback) + MCP servers
- CLI: Git, gh, just, jq, tmux, delta, and more
- AI: Claude Code, Claude Desktop

The installer is idempotent — safe to re-run anytime.

---

## Project Scaffolding

Seed new or existing projects with cross-vendor AI rules that work with Claude Code, Cursor, and Gemini CLI.

### Usage

One script, idempotent — run it on new or existing projects:

```bash
# Create new projects
~/dotfiles/prompts/scaffold.sh typescript my-app           # SvelteKit (default)
~/dotfiles/prompts/scaffold.sh typescript astro my-blog    # Astro
~/dotfiles/prompts/scaffold.sh python my-api               # FastAPI (default)
~/dotfiles/prompts/scaffold.sh golang my-service           # Chi (default)
~/dotfiles/prompts/scaffold.sh rust my-tool                # Axum (default)

# Seed existing projects (use . for current directory)
~/dotfiles/prompts/scaffold.sh typescript .
~/dotfiles/prompts/scaffold.sh python ~/code/my-api
```

Safe to run multiple times -- only adds missing pieces. AGENTS.md is generated once, then project-owned (use `--force` to regenerate).

This adds cross-vendor AI rules — lightweight scaffolding that guides AI agents:

```
my-project/
├── AGENTS.md              # ~30 lines: pointers + project context (project-owned)
├── .ai/rules/*.mdc        # AI rules (universal=symlinked, recipe=copied)
├── .cursor/rules/*.mdc    # Cursor symlinks → .ai/rules/ (auto-generated)
├── .agents/               # Working files, gitignored (plans, research, sessions)
└── .agents/decisions/     # Architecture Decision Records (versioned)
```

**How rules are deployed:**
- **Universal rules** (process, style) are symlinked — auto-update from dotfiles
- **Recipe rules** (language, framework, stack) are copied — project can customize
- **Cursor symlinks** are auto-generated relative links to `.ai/rules/`
- Only rules relevant to the recipe are deployed, not the entire library

### Available Recipes

| Recipe | App Type | Stack | Use Case |
|--------|----------|-------|----------|
| `typescript` | `svelte` (default) | Bun + SvelteKit 2 + Svelte 5 | Full-stack apps |
| `typescript` | `astro` | Bun + Astro | Content sites, blogs |
| `python` | `fastapi` (default) | UV + FastAPI + SQLAlchemy | APIs, AI services |
| `golang` | `chi` (default) | Go 1.25+ Chi router + sqlc | APIs, services |
| `rust` | `axum` (default) | Tokio + Axum + SQLx | APIs, services |
| `rust` | `tauri` | Tauri 2 + SvelteKit | Desktop apps |

---

## What's Installed

### Shell & Terminal

- **Zsh + Oh My Zsh**: Battle-tested shell framework
- **Custom theme**: Two-line prompt with git branch status
- **Rectangle**: Window management

### Runtimes

| Runtime | Manager | Notes |
|---------|---------|-------|
| **Node.js** | fnm | LTS version, auto-switches per project |
| **Bun** | direct | Preferred JS runtime (faster than Node) |
| **Python** | uv | Python 3.14, fast package management |

> **Go** is available but disabled by default — enable in `brew.sh` and `install.sh` if needed.

### Editors

- **Cursor**: Primary editor (AI-native, VS Code compatible, MCP servers configured)
- **VS Code**: Fallback when needed

Both share the same extension list. See `editors/` for configs.

### CLI Tools

| Category | Tools |
|----------|-------|
| **Git** | delta (diffs), gh (GitHub CLI) |
| **Task runner** | just |
| **Data** | jq, yq |
| **Utils** | tmux, ripgrep, fd, bat, eza |

### AI Tools

| Tool | Purpose |
|------|---------|
| **Claude Code** | Agentic coding assistant (CLI) |
| **Claude Desktop** | Claude macOS app |

### MCP Servers (Cursor)

| Server | Purpose |
|--------|---------|
| **Exa** | AI-powered web search for research |
| **Linear** | Issue tracking integration |
| **Notion** | Documentation integration |
| ~~Datadog~~ | Observability (disabled, enable when needed) |

Configure API keys in `~/.cursor/mcp.json` (symlinked from `editors/cursor/mcp.json`).

---

## Configuration

### Homebrew

Edit `macos/brew.sh` to customize packages. Organized by category with opt-in toggles:

```bash
AI=1 PRODUCTIVITY=1 SOCIAL=0 ~/dotfiles/macos/brew.sh
```

### The `dotfiles` Command

```bash
dotfiles help        # Show available commands
dotfiles doctor      # Check all tools are installed correctly
dotfiles update      # Update OS, Homebrew, and Node.js LTS
dotfiles clean       # Clear Homebrew caches
dotfiles brew        # Re-run Homebrew setup
dotfiles dock        # Reset Dock layout
dotfiles completions # Output shell completions (source in .zshrc)
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
├── editors/                # Cursor + VS Code settings
├── macos/                  # Homebrew, Dock, SSH setup
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
