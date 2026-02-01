# Dotfiles

Opinionated Mac setup scripts + configs, optimized for a fast, clean dev machine.

## What you get

- **Shell**: Zsh + Oh My Zsh + a custom theme (`shell/amuse.zsh-theme`)
- **Dev runtimes**:
  - **Rust**: `rustup` + Cargo
  - **Node.js**: `fnm` (Fast Node Manager) + Node LTS + Corepack (pnpm/yarn)
  - **Bun**: JavaScript runtime + package manager
  - **Python**: `uv` + Python 3.12
- **Homebrew**: curated packages + apps via `macos/brew.sh`
- **macOS**: Dock setup via `macos/dock.sh`
- **Editors**: VS Code & Cursor configurations via `editors/`
  - Shared extension list (VS Code gets Supermaven; Cursor uses built-in AI)
  - Editor-specific settings and Cursor AI rules
- **Git**: `.gitconfig` + `.gitignore_global`
- **DX tools**: `just` (command runner), `jq`, `tmux`, and more
- **Recipe Book**: Opinionated project templates for AI-assisted development (`prompts/`)

## Install (fresh macOS)

1. **Update macOS + install Xcode CLT**

```bash
sudo softwareupdate -i -a
xcode-select --install
```

2. **Clone and run**

```bash
git clone https://github.com/e-m-albright/dotfiles ~/dotfiles
chmod +x ~/dotfiles/install.sh
chmod -R +x ~/dotfiles/bin
~/dotfiles/install.sh
```

**What happens**: The installer sets up your shell, installs all Homebrew packages, configures Git, installs Node.js LTS (via fnm), sets up Rust/Python/Bun, installs Marimo (Python notebooks), installs VS Code/Cursor extensions, and configures your Dock. After completion, you'll have a fully configured dev environment ready for Next.js, React, Python, and more.

**Idempotent & safe to re-run**: The installer is designed to be safe to run multiple times. It checks for existing installations before installing, uses idempotent operations (symlinks, checks), and won't overwrite your customizations. You can safely run `./install.sh` after adding new tools to `macos/brew.sh` or updating configs.

## Homebrew (curation + toggles)

**Configuration**: Edit `macos/brew.sh` directly to manage your tool selection. Packages are organized in bash arrays by category:
- Add/remove packages by editing the arrays
- Switch IDEs by commenting/uncommenting inline
- Comment out tools inline (right where they "would live")

No dependencies needed - just edit the bash arrays and re-run the script.

**Installation**: `macos/brew.sh` supports opt-in toggles:

- **AI**: `AI=1` (default) installs AI CLI tools and local model runner
- **Productivity**: `PRODUCTIVITY=1` (default) installs window/clipboard helpers
- **Social**: `SOCIAL=1` (default) installs chat/music/etc.

Example:

```bash
AI=1 PRODUCTIVITY=1 SOCIAL=0 ~/dotfiles/macos/brew.sh
```

**IDEs**: The config includes a curated list of editors; you keep exactly one enabled at a time by commenting/uncommenting inline.

## AI tools

This repo currently supports AI tooling in three ways:

- **Editors** (configured via `editors/` directory)
  - **VS Code**: 
    - `editors/vscode/settings.json` - Editor settings
    - `editors/vscode/extensions.sh` - Extension installer (uses shared list)
    - Includes Supermaven for AI autocomplete
  - **Cursor**: 
    - `editors/cursor/settings.json` - VS Code-compatible editor settings
    - `editors/cursor/cli-config.json` - Global Cursor CLI configuration (AI agent permissions, modes)
    - `editors/cursor/CursorRules.md` - Project-level AI agent rules template
    - `editors/cursor/.cursorignore` - Files to exclude from AI context
    - `editors/cursor/extensions.sh` - Extension installer (uses shared list, excludes Supermaven)
    - Referenced in `macos/dock.sh` (Dock pin)
  - **Shared**: `editors/extensions.sh` - Common extension list (both editors use this)
- **CLI agents**
  - **Claude Code**: installed via Homebrew when available (`macos/brew.sh`, AI category).
  - **Gemini CLI**: installed via Homebrew when available (`macos/brew.sh`, AI category).
- **Local models**
  - **Ollama**: installed via Homebrew (`macos/brew.sh`, AI category).
  - Optional UI (manual): `open-webui` via `uv` (see below).

### New AI gizmos (optional)

In `macos/brew.sh` under `ai_gizmos` there's a small "AI-adjacent" list (mostly commented out) for tools like:
- **Raycast** (launcher/workflows)
- **Warp** (modern AI terminal)

### What you already use (but this repo doesn't fully automate yet)

- **Antigravity**: not currently installed/configured by these scripts; add it to `macos/brew.sh` (AI category) or document a manual install step once you decide the preferred distribution method.

### ML/DL Development

For deep learning and ML development (PyTorch, JAX, etc.), see **[ML_SETUP.md](ML_SETUP.md)** for:
- Recommended Python packages (PyTorch, JAX, Weights & Biases, Hugging Face, etc.)
- CLI tools (huggingface-cli, already included)
- VS Code/Cursor extensions (Jupyter, TensorBoard)
- Workflow recommendations and what teams like Anthropic use

### Local model quickstart (Ollama)

```bash
ollama serve
ollama pull llama3.2
```

### Optional: Open WebUI (via uv)

```bash
uv tool install open-webui
uv tool run open-webui serve
```

## The `dotfiles` command

```bash
dotfiles help
```

Commands (see `bin/dotfiles`):

- **help**: show help
- **update**: update OS + package managers
- **clean**: clean caches
- **brew**: run the Homebrew installer (`macos/brew.sh`)
- **dock**: run Dock setup (`macos/dock.sh`)

## Node.js / Next.js development

After installation, you're ready for Next.js development:

```bash
# Node.js LTS is already installed via fnm
node --version

# Corepack is enabled (pnpm/yarn support)
pnpm --version  # or yarn --version

# Create a Next.js project
pnpm create next-app@latest my-app
# or
npx create-next-app@latest my-app
```

**What's included**:
- **fnm**: Fast Node Manager (faster than nvm)
- **Node.js LTS**: Automatically installed and set as default
- **Corepack**: Enabled for pnpm/yarn (no separate install needed)
- **npm**: Comes with Node.js
- **VS Code extensions**: ESLint, Prettier, TailwindCSS, and more

## Shell choice: Oh My Zsh

**Why Oh My Zsh?** Oh My Zsh is still the best-in-class framework for ZSH:

- **Massive ecosystem**: 200+ plugins, 150+ themes, huge community
- **Easy customization**: Simple plugin/theme system, well-documented
- **Battle-tested**: Used by millions, stable and reliable
- **Great defaults**: Sensible ZSH options, useful aliases out of the box
- **Plugin ecosystem**: Git, Docker, Node, Python, Rust plugins ready to go
- **Performance**: Fast startup, efficient completion system

**Alternatives considered**:
- **Prezto**: Lighter but smaller plugin ecosystem
- **Zinit/Zplugin**: More powerful but steeper learning curve
- **Starship**: Great prompt but not a full framework
- **No framework**: More control but more setup work

For a macOS-focused dev setup, Oh My Zsh provides the best balance of ease-of-use, ecosystem size, and customization. It's the "batteries included" approach that gets you productive fast.

## Notes / future tweaks

- **Caffeine**: Intel-only (requires Rosetta); included in config but you may want to skip it on Apple Silicon.
- **Rectangle vs Raycast**: Rectangle is the current default; Raycast is a great alternative if you want to consolidate window management + launcher.

## Recipe Book (AI-Assisted Development)

The `prompts/` directory contains opinionated project templates ("recipes") designed for AI-assisted development. Each recipe includes:

- **AGENTS.md**: Cross-platform instructions for AI coding agents (Claude, Cursor, Gemini, ChatGPT)
- **STACK.md**: Tech stack decisions with rationale (why X over Y)
- **STYLE.md**: Code style guide
- **templates/**: Starter files (`.gitignore`, `justfile`, configs)
- **skills/**: Agent skills for specific frameworks

### Available Recipes

| Recipe | Stack | Use Case |
|--------|-------|----------|
| `typescript` | Bun + SvelteKit 2 + Svelte 5 + Tailwind v4 + Drizzle | Full-stack web apps |
| `python` | UV + FastAPI + Pydantic v2 + SQLAlchemy 2.0 | APIs, ML services |
| `golang` | Go 1.22+ stdlib + sqlc + pgx | High-performance services |

### Quick Start

```bash
# Create a new project from a recipe
recipe typescript my-web-app

# Or manually
cd ~/code
~/dotfiles/prompts/init.sh python my-api
```

### What Gets Created

```
my-project/
├── AGENTS.md           # Symlinked from recipe (AI instructions)
├── PROJECT_BRIEF.md    # Template for you to describe your project
├── .agents/            # Directory for AI agent output
│   ├── plans/          # Implementation plans
│   ├── research/       # Investigation notes
│   └── scratch/        # Temporary work
├── .gitignore
├── justfile
└── [recipe-specific files]
```

### Philosophy

- **One pick per category**: No "it depends." Every choice is justified.
- **Agent-first**: All configs work with Claude, Cursor, Gemini, ChatGPT.
- **Human-readable**: Every file is organized, commented, and skimmable.
- **DX-optimized**: Fast feedback loops, minimal config, maximum productivity.

For detailed documentation, see [`prompts/README.md`](prompts/README.md).

## Credits

- https://dotfiles.github.io/
- https://github.com/webpro/awesome-dotfiles
- https://github.com/mathiasbynens/dotfiles