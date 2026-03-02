# Project Recipes

Opinionated scaffolding for TypeScript, Python, and Go projects -- optimized for AI-assisted development and long-term maintainability.

**Philosophy**: Dotfiles seeds and influences. Projects own themselves.

## Usage

One script, idempotent -- run it on new or existing projects:

```bash
# Create new projects
~/dotfiles/prompts/scaffold.sh typescript my-app           # SvelteKit (default)
~/dotfiles/prompts/scaffold.sh typescript astro my-blog    # Astro
~/dotfiles/prompts/scaffold.sh python my-api               # FastAPI (default)
~/dotfiles/prompts/scaffold.sh golang my-service           # Chi (default)

# Seed existing projects (use . for current directory)
~/dotfiles/prompts/scaffold.sh typescript .
~/dotfiles/prompts/scaffold.sh python ~/code/my-api

# Force regenerate everything (including AGENTS.md)
~/dotfiles/prompts/scaffold.sh --force python .
```

Safe to run multiple times -- only adds missing pieces. AGENTS.md is generated once, then project-owned (use `--force` to regenerate).

### What Gets Created

| File/Directory | Purpose | Ownership |
|----------------|---------|-----------|
| `AGENTS.md` | Project instructions + context (code patterns + project brief) | Project-owned (edit freely) |
| `.cursor/rules/*.mdc` | Cursor rules for process, safety, and coding conventions | Universal = symlinked, Recipe = copied |
| `.agents/` | Working files: plans, research, sessions (gitignored) | Project-owned |
| `.agents/decisions/` | Architecture Decision Records (versioned) | Project-owned |

### On Re-run

- **AGENTS.md** -- NOT overwritten (project owns it). Use `--force` to regenerate.
- **Universal rules** -- re-symlinked (always up to date from dotfiles).
- **Recipe rules** -- skip existing files (project may have customized).
- **.agents/** -- created if missing, `decisions/` subdirectory ensured.

### Bringing an Existing Project into Conformance

```bash
cd ~/code/my-existing-app

# 1. Scaffold to add rules and generate AGENTS.md
~/dotfiles/prompts/scaffold.sh python .

# 2. Edit the 'Project Context' section in AGENTS.md

# 3. Audit against our guidelines
claude "Read AGENTS.md and .cursor/rules/. Audit this codebase. Create a
report in .agents/research/ listing what conforms, what needs to change,
and recommended priority. Don't change anything yet."

# 4. Plan the conformance
claude "Create a phased plan in .agents/plans/ to bring this project
into conformance. Each phase should be safe and incremental."

# 5. Execute incrementally
claude "Execute phase 1. Run tests after each change."
```

---

## Available Recipes

| Recipe | App Type | Stack | Use Case |
|--------|----------|-------|----------|
| `typescript` | `svelte` (default) | Bun + SvelteKit 2 + Svelte 5 + pino | Full-stack apps |
| `typescript` | `astro` | Bun + Astro 6 | Content sites, blogs |
| `python` | `fastapi` (default) | UV + FastAPI + SQLAlchemy | APIs, AI services |
| `golang` | `chi` (default) | Go 1.25+ Chi router + sqlc | APIs, services |

### TypeScript

Two framework choices within the same ecosystem (Bun, Biome, Tailwind, pino):

| Framework | Use Case |
|-----------|----------|
| **SvelteKit** | Full-stack apps -- SSR, API routes, forms, auth |
| **Astro** | Content sites -- blogs, portfolios, docs, marketing |

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
├── BASE.md               # Shared code patterns (logging, testing, errors)
├── STACK.md              # Tech stack choices + rationale
├── framework/            # Framework-specific patterns
│   └── FRAMEWORK.md      # Combined with BASE.md at scaffold time
├── skills/               # Agent skills for specific tools
│   └── SKILL.md
└── templates/            # Starter files (.gitignore, justfile, etc.)
```

At scaffold time: BASE.md + FRAMEWORK.md become the "Code Patterns" section of the generated AGENTS.md. Behavioral rules (git safety, tickets, critical rules) live in `.cursor/rules/*.mdc` files instead.

---

## Project Organization

### Two-Layer System

```
Layer 1: CURRENT STATE (project-owned, curated)
├── AGENTS.md               # Project instructions + context
└── .cursor/rules/*.mdc     # Behavioral rules (symlinked + project-specific)

Layer 2: WORKING CONTEXT (.agents/)
├── .agents/decisions/      # Architecture Decision Records (versioned)
├── .agents/plans/          # Implementation plans (gitignored)
├── .agents/research/       # Investigation notes (gitignored)
└── .agents/sessions/       # Conversation logs (gitignored)
```

---

## AI Agent Integration

### Claude Code / Gemini

AGENTS.md is automatically loaded from project root. It includes a pointer to read `.cursor/rules/` for behavioral rules.

### Cursor

`.cursor/rules/*.mdc` files are loaded natively with glob-based scoping and always-apply support.

---

## Philosophy

- **One pick per category** -- No "it depends." Every choice is justified.
- **Start minimal** -- Add tools when you need them, not before.
- **Projects own themselves** -- Dotfiles seeds good defaults; projects can diverge.
- **Agent-first** -- All configs work with Claude, Cursor, Gemini, ChatGPT.

---

## Shared Infrastructure

See `shared/` for cross-language guides:

| Guide | Contents |
|-------|----------|
| `SERVICES.md` | Cloud services (hosting, database, auth, etc.) |
| `INFRASTRUCTURE.md` | Docker, Pulumi, observability |
| `AI_TOOLS.md` | AI development workflow |
| `CUSTOMER_DISCOVERY.md` | Customer interview questions & exploration areas |
| `PROJECT_MEMORY.md` | Decision organization system |
