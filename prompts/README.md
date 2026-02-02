# Project Recipes

Opinionated scaffolding for TypeScript, Python, and Go projects — optimized for AI-assisted development and long-term maintainability.

## Usage

One script, idempotent — run it on new or existing projects:

```bash
# Create new projects
~/dotfiles/prompts/scaffold.sh typescript my-app           # SvelteKit (default)
~/dotfiles/prompts/scaffold.sh typescript astro my-blog    # Astro
~/dotfiles/prompts/scaffold.sh python my-api               # FastAPI (default)
~/dotfiles/prompts/scaffold.sh golang my-service           # Chi (default)

# Seed existing projects (use . for current directory)
~/dotfiles/prompts/scaffold.sh typescript .
~/dotfiles/prompts/scaffold.sh typescript astro ~/code/my-blog
~/dotfiles/prompts/scaffold.sh python ~/code/my-api
```

Safe to run multiple times — only adds missing pieces, regenerates AGENTS.md to pick up recipe updates.

### What Gets Added

| File/Directory | Purpose |
|----------------|---------|
| `AGENTS.md` | Instructions for AI agents (generated from BASE.md + FRAMEWORK.md) |
| `ABSTRACT.md` | What you're building (you fill this in) |
| `.agents/` | Working files: plans, research, sessions (gitignored) |
| `.architecture/` | Architecture Decision Records (versioned) |

### Bringing an Existing Project into Conformance

```bash
cd ~/code/my-existing-app

# 1. Fill out ABSTRACT.md first

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

| Recipe | App Type | Stack | Use Case |
|--------|----------|-------|----------|
| `typescript` | `svelte` (default) | Bun + SvelteKit 2 + Svelte 5 + pino | Full-stack apps |
| `typescript` | `astro` | Bun + Astro 4 | Content sites, blogs |
| `python` | `fastapi` (default) | UV + FastAPI + SQLAlchemy | APIs, AI services |
| `golang` | `chi` (default) | Go 1.22+ Chi router + sqlc | APIs, services |

### TypeScript

Two framework choices within the same ecosystem (Bun, Biome, Tailwind, pino):

| Framework | Use Case |
|-----------|----------|
| **SvelteKit** | Full-stack apps — SSR, API routes, forms, auth |
| **Astro** | Content sites — blogs, portfolios, docs, marketing |

Use Astro for content-heavy sites. Use SvelteKit for interactive apps. Both can use Svelte components.

### Python

FastAPI-focused recipe for APIs and services:

- **APIs**: FastAPI for REST/GraphQL
- **ML/AI**: PydanticAI, Instructor (see [ML.md](./python/ML.md))
- **CLI**: Typer for command-line tools

### Golang

Chi router for APIs and services:

- APIs with composable middleware
- Background workers and data pipelines
- CLI tools and system utilities

---

## Recipe Structure

Each recipe contains:

```
recipe-name/
├── BASE.md               # Shared patterns (logging, testing, errors)
├── STACK.md              # Tech stack choices + rationale
├── framework/            # Framework-specific patterns
│   └── FRAMEWORK.md      # Combined with BASE.md at scaffold time
├── skills/               # Agent skills for specific tools
│   └── SKILL.md
└── templates/            # Starter files (.gitignore, justfile, etc.)
```

When you run `scaffold.sh`, it concatenates `BASE.md` + `FRAMEWORK.md` into a single `AGENTS.md` in your project.

---

## Project Organization

### Three-Layer Memory System

```
Layer 1: CURRENT STATE (curated, ~300-500 lines)
├── AGENTS.md             # Project instructions (AI + humans)
└── ABSTRACT.md           # What we're building

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
ln -s AGENTS.md .cursorrules
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
