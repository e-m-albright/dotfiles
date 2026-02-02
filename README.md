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
- Runtimes: Bun, Node.js (fnm), Python (uv), Go
- Editor: Cursor (with VS Code as fallback)
- CLI: Git, just, jq, tmux, delta, and more
- AI: Claude Code, Gemini CLI, Ollama

The installer is idempotent — safe to re-run anytime.

---

## Project Scaffolding

The `prompts/` directory contains opinionated recipes for TypeScript, Python, and Go projects.

### New Project (Seed)

Create a fresh project with our full skeleton:

```bash
~/dotfiles/prompts/init.sh typescript my-app
~/dotfiles/prompts/init.sh python my-api
~/dotfiles/prompts/init.sh golang my-service
```

### Existing Project (Rails)

Add our project structure to an existing codebase:

```bash
~/dotfiles/prompts/seed.sh typescript ~/code/my-existing-app
```

This adds the **rails** — lightweight scaffolding that guides AI agents and keeps projects maintainable:

```
my-project/
├── AGENTS.md           # Instructions for AI agents (symlinked from recipe)
├── ABSTRACT.md    # What you're building (you fill this in)
├── .agents/            # Working files, gitignored (plans, research, sessions)
└── .architecture/      # Architecture decisions, versioned (ADRs)
```

Then use Claude Code to bring the project into conformance:

```bash
cd ~/code/my-existing-app

# Audit against our guidelines
claude "Read AGENTS.md and audit this codebase. List what conforms,
what needs to change, and recommended priority. Don't change anything yet."

# Create a conformance plan
claude "Create a phased plan in .agents/plans/ to bring this project
into conformance. Each phase should be safe and incremental."

# Execute incrementally
claude "Execute phase 1. Run tests after each change."
```

### Available Recipes

| Recipe | Runtime | Framework | Use Case |
|--------|---------|-----------|----------|
| `typescript` | Bun | SvelteKit / Astro | Full-stack apps, content sites |
| `python` | UV | FastAPI / Reflex | APIs, AI services, analytics |
| `golang` | Go 1.22+ | stdlib + sqlc | High-performance services |

See [`prompts/README.md`](prompts/README.md) for the full recipe documentation.

---

## What's Installed

### Shell & Terminal

- **Zsh + Oh My Zsh**: Battle-tested shell framework
- **Custom theme**: Two-line prompt with git branch status
- **Warp**: Modern terminal with AI features

### Runtimes

| Runtime | Manager | Notes |
|---------|---------|-------|
| **Node.js** | fnm | LTS version, auto-switches per project |
| **Bun** | direct | Preferred JS runtime (faster than Node) |
| **Python** | uv | Python 3.12, fast package management |
| **Go** | brew | Go 1.22+, with gopls, delve, air, sqlc, templ |

### Editors

- **Cursor**: Primary editor (AI-native, VS Code compatible)
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
| **Claude Code** | Agentic coding assistant |
| **Gemini CLI** | Google's CLI assistant |
| **Ollama** | Local model runtime |

---

## Configuration

### Homebrew

Edit `macos/brew.sh` to customize packages. Organized by category with opt-in toggles:

```bash
AI=1 PRODUCTIVITY=1 SOCIAL=0 ~/dotfiles/macos/brew.sh
```

### The `dotfiles` Command

```bash
dotfiles help      # Show available commands
dotfiles update    # Update OS + package managers
dotfiles clean     # Clear caches
dotfiles brew      # Re-run Homebrew setup
dotfiles dock      # Reset Dock layout
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
└── prompts/                # Project recipes + scaffolding
    ├── typescript/         # SvelteKit / Astro recipe
    ├── python/             # FastAPI / Reflex recipe
    ├── golang/             # Go recipe
    ├── shared/             # Cross-language guides
    └── templates/          # ABSTRACT.md template
```

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
