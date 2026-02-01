# Project Recipes

Opinionated scaffolding for TypeScript, Python, and Go projects — optimized for AI-assisted development and long-term maintainability.

## Two Operations

### 1. Seed a New Project

Create a fresh project with the full skeleton:

```bash
~/dotfiles/prompts/init.sh typescript my-app
~/dotfiles/prompts/init.sh python my-api ~/projects
~/dotfiles/prompts/init.sh golang my-service
```

You get a git-initialized project with all configs, ready to develop.

### 2. Add Rails to an Existing Project

Add our lightweight scaffolding to an existing codebase:

```bash
~/dotfiles/prompts/seed.sh typescript ~/code/my-existing-app
```

This adds **rails** — the minimal structure that guides AI agents and keeps projects organized:

| File/Directory | Purpose |
|----------------|---------|
| `AGENTS.md` | Instructions for AI agents (symlinked from recipe) |
| `PROJECT_BRIEF.md` | What you're building (you fill this in) |
| `.agents/` | Working files: plans, research, sessions (gitignored) |
| `.architecture/` | Architecture Decision Records (versioned) |

Then use Claude Code to bring the project into conformance:

```bash
cd ~/code/my-existing-app

# 1. Fill out PROJECT_BRIEF.md first

# 2. Audit against our guidelines
claude "Read AGENTS.md and audit this codebase. Create a report listing
what conforms, what needs to change, and recommended priority. Don't
change anything yet."

# 3. Plan the conformance
claude "Create a phased plan in .agents/plans/ to bring this project
into conformance. Each phase should be safe and incremental."

# 4. Execute incrementally
claude "Execute phase 1. Run tests after each change."
```

---

## Available Recipes

| Recipe | Runtime | Framework | Use Case |
|--------|---------|-----------|----------|
| [typescript](./typescript/) | Bun | SvelteKit / Astro | Full-stack apps, content sites |
| [python](./python/) | UV | FastAPI / Reflex | APIs, AI services, analytics |
| [golang](./golang/) | Go 1.22+ | stdlib + sqlc | High-performance services |

### TypeScript

Two framework choices within the same ecosystem (Bun, Biome, Tailwind):

| Framework | Use Case |
|-----------|----------|
| **SvelteKit** | Full-stack apps — SSR, API routes, forms, auth |
| **Astro** | Content sites — blogs, portfolios, docs, marketing |

Use Astro for content-heavy sites. Use SvelteKit for interactive apps. Both can use Svelte components.

### Python

Flexible recipe covering multiple use cases:

- **APIs**: FastAPI for REST/GraphQL
- **Full-Stack**: Reflex for Python-native UIs
- **Analytics**: Polars + DuckDB + Marimo notebooks
- **ML/AI**: PyTorch, JAX, vLLM (see [ML.md](./python/ML.md))
- **CLI**: Typer for command-line tools
- **Scripts**: Simple UV scripts

### Golang

Optimized for high-performance services:

- APIs with minimal dependencies
- Background workers and data pipelines
- CLI tools and system utilities

---

## Recipe Structure

Each recipe contains:

```
recipe-name/
├── AGENTS.md             # AI agent instructions (symlinked into projects)
├── STACK.md              # Tech stack choices + rationale
├── STYLE.md              # Code style guide
├── skills/               # Agent skills for specific tools
│   └── SKILL.md
└── templates/            # Starter files (.gitignore, justfile, etc.)
```

---

## Project Organization

### Three-Layer Memory System

```
Layer 1: CURRENT STATE (curated, ~300-500 lines)
├── AGENTS.md             # Project instructions (AI + humans)
└── PROJECT_BRIEF.md      # What we're building

Layer 2: DECISION HISTORY (append-only, versioned)
├── .architecture/adr/*.md   # Architecture Decision Records
└── .architecture/CHANGELOG.md

Layer 3: WORKING CONTEXT (ephemeral, gitignored)
├── .agents/plans/        # Implementation plans
├── .agents/research/     # Investigation notes
└── .agents/sessions/     # Conversation logs
```

### Decision Attribution

| Tag | Meaning |
|-----|---------|
| 👤 HUMAN | Human made this call |
| 🤖 AI-SUGGESTED | AI proposed, human approved |
| 🤖→👤 AI-REFINED | AI explored, human decided |
| ⚠️ ASSUMED | Nobody explicitly decided (validate this) |

---

## AI Agent Integration

### Claude Code

```bash
# AGENTS.md is automatically loaded from project root
```

### Cursor

```bash
# Symlink or copy to .cursorrules
ln -s ~/dotfiles/prompts/typescript/AGENTS.md .cursorrules
```

### Gemini / ChatGPT

Paste AGENTS.md content at the start of your conversation.

---

## Philosophy

- **One pick per category** — No "it depends." Every choice is justified.
- **Start minimal** — Add tools when you need them, not before.
- **Agent-first** — All configs work with Claude, Cursor, Gemini, ChatGPT.
- **Human-readable** — Every file is organized, commented, and skimmable.

---

## Shared Infrastructure

See `shared/` for cross-language guides:

| Guide | Contents |
|-------|----------|
| `SERVICES.md` | Cloud services (hosting, database, auth, etc.) |
| `INFRASTRUCTURE.md` | Docker, Pulumi, observability |
| `AI_TOOLS.md` | AI development workflow |
| `PROJECT_MEMORY.md` | Decision organization system |
