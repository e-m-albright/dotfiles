# Prompts

Opinionated recipe book for bootstrapping new projects with best-in-class tech stacks.

Each recipe is a complete, production-ready configuration that can be used to:
1. **Seed a new project** with optimal defaults
2. **Bring existing projects into compliance** with modern standards
3. **Guide AI coding agents** with consistent, high-quality instructions

## Philosophy

- **One pick per category** — No "it depends." Every choice is justified.
- **Start minimal, add as needed** — Recipes are menus, not mandates. Pick only what you need.
- **Agent-first** — All configs work with Claude, Cursor, Gemini, ChatGPT.
- **Human-readable** — Every file is organized, commented, and skimmable.
- **DX-optimized** — Fast feedback loops, minimal config, maximum productivity.

### Start Minimal

**These recipes are curated selections, not checklists.** A backend service doesn't need frontend libraries. A simple API doesn't need DuckDB. An exploration script doesn't need a full web framework.

When starting a project:
1. **Pick the core** — Runtime, framework, database (if needed)
2. **Add incrementally** — Bring in tools when you actually need them
3. **Reference the menu** — When you need analytics, check STACK.md for our pick

The STACK.md files show what's available. The AGENTS.md files tell agents what's installed. Don't install everything upfront — that's how projects become unmaintainable.

## Available Recipes

| Recipe | Runtime | Framework | Use Case |
|--------|---------|-----------|----------|
| [typescript](./typescript/) | Bun | SvelteKit 2 + Svelte 5 | Full-stack web apps |
| [python](./python/) | UV | FastAPI / Reflex / Scripts | APIs, AI services, analytics, full-stack |
| [golang](./golang/) | Go 1.22+ | stdlib + sqlc | High-performance services |

### Python Recipe Flexibility

The Python recipe isn't just for APIs. It covers:
- **APIs & Services**: FastAPI for REST/GraphQL endpoints
- **Background Workers**: Arq for async task queues, AI pipelines
- **Analytics & Exploration**: Polars + DuckDB + Marimo notebooks
- **Full-Stack Apps**: Reflex for Python-native web UIs
- **CLI Tools**: Typer for command-line applications
- **Scripts**: Simple UV scripts for automation

### TypeScript Recipe Focus

The TypeScript recipe is optimized for **web applications**:
- SvelteKit handles full-stack (SSR, API routes, client)
- Can be extended with Tauri for desktop distribution
- Includes options for analytics (DuckDB, Polars.js) when needed

### Golang Recipe Focus

The Golang recipe is optimized for **high-performance services**:
- APIs with minimal dependencies
- Background workers and data pipelines
- CLI tools and system utilities

## Recipe Structure

Each recipe contains:

```
recipe-name/
├── STACK.md              # Tech stack menu + rationale
├── AGENTS.md             # Cross-platform agent instructions
├── STYLE.md              # Code style guide
├── skills/               # Agent skills for specific tools
│   └── SKILL.md
├── templates/            # Minimal starter files
│   ├── .gitignore
│   ├── justfile
│   └── ...
└── extras/               # Optional configs to add later
    ├── docker/
    └── infra/
```

## Quick Start

### New Project

```bash
# From your dotfiles
recipe typescript my-new-app

# Or directly
~/dotfiles/prompts/init.sh python my-api
```

### Existing Project

```bash
# Copy the AGENTS.md to your project root
cp ~/dotfiles/prompts/typescript/AGENTS.md ./AGENTS.md

# Copy specific configs as needed
cp ~/dotfiles/prompts/typescript/templates/biome.json .
```

## AI Development Tools

See `shared/AI_TOOLS.md` for the complete guide. Quick picks:

| Task | Tool | Notes |
|------|------|-------|
| **Complex coding** | Claude Code | Agentic, multi-file, autonomous |
| **Quick iteration** | Cursor | IDE-integrated, fast feedback |
| **Full-stack MVP** | bolt.new | 10-20 min prototypes |
| **React components** | v0.dev | Then adapt to Svelte |
| **Svelte components** | Claude Code | More reliable than specialized tools |

### Workflow

```
Feature Development:
1. Claude Code → Design + architecture
2. Claude Code → Initial implementation
3. Cursor → Refinement + debugging
4. Manual → Code review + testing
```

## Agent Integration

### Claude Code
```bash
# AGENTS.md is automatically loaded from project root
# Skills can be installed globally or per-project
```

### Cursor
```bash
# Copy AGENTS.md content to .cursorrules or .cursor/rules/
cp ~/dotfiles/prompts/typescript/AGENTS.md .cursorrules
```

### Gemini / ChatGPT
```bash
# Paste AGENTS.md content at the start of your conversation
```

## Project Organization

See `shared/PROJECT_MEMORY.md` for the complete decision organization system.

### Three-Layer Memory System

```
Layer 1: CURRENT STATE (Living, curated, ~300-500 lines)
├── AGENTS.md             # How we build (tech stack, patterns)
└── PROJECT_BRIEF.md      # What we're building (context)

Layer 2: DECISION HISTORY (Immutable, append-only)
├── decisions/adr/*.md    # Architecture Decision Records
└── decisions/CHANGELOG.md # Timeline with attribution

Layer 3: SESSION CONTEXT (Ephemeral, gitignored)
├── .agents/plans/        # Implementation plans
├── .agents/research/     # Investigation notes
├── .agents/scratch/      # Temporary work
└── .agents/sessions/     # Conversation logs
```

### Decision Attribution

Track who made decisions and how:

| Tag | Meaning | Durability |
|-----|---------|------------|
| 👤 HUMAN | Explicit human decision | Durable, don't challenge |
| 🤖 AI-SUGGESTED | AI proposed, human approved | Inspectable, can revisit |
| 🤖→👤 AI-REFINED | AI explored, human decided | Hybrid attribution |
| ⚠️ ASSUMED | Implicit assumption | Flag for validation |

### Directory Structure

```
your-project/
├── AGENTS.md                    # Layer 1: Current state
├── PROJECT_BRIEF.md             # Layer 1: Project context
├── decisions/                   # Layer 2: Decision history
│   ├── adr/                     # Architecture Decision Records
│   │   ├── 0001-database.md
│   │   └── _index.md
│   └── CHANGELOG.md             # Decision timeline
├── .agents/                     # Layer 3: Session memory (gitignored)
│   ├── plans/
│   ├── research/
│   ├── scratch/
│   └── sessions/
└── ...
```

## Shared Infrastructure

These apply across all recipes when needed:

### Containerization
- **Docker**: Dockerfile + docker-compose for local dev
- **Multi-stage builds**: Minimize production images

### Infrastructure as Code
- **Pulumi** over Terraform — Real programming languages, better state management

### Cloud Services

See `shared/SERVICES.md` for the full menu. Quick picks:

| Category | Primary Pick | Notes |
|----------|-------------|-------|
| **Hosting** | Railway | Or Cloudflare for edge/static |
| **Database** | Supabase | Postgres + extras. Or Neon for pure Postgres. |
| **Search** | Meilisearch | Self-host first, Cloud when needed |
| **Email** | Resend | Modern DX, React Email support |
| **Auth** | Better Auth | Self-hosted, TypeScript-first |
| **Analytics** | Umami | Privacy-first, self-hosted |
| **Cache** | Valkey | Redis fork, self-hosted |
| **Payments** | Stripe | Industry standard |

### Observability

| Tier | Tools | When |
|------|-------|------|
| **Tier 1** | structlog/pino + Sentry | All projects |
| **Tier 2** | + OpenTelemetry | 2+ services |
| **Tier 3** | + Jaeger + Grafana | At scale |

See `shared/INFRASTRUCTURE.md` for setup details.

### Documentation (add when needed, not at start)
- **TypeScript**: VitePress or Starlight
- **Python**: MkDocs + Material theme
- **Golang**: Built-in godoc or MkDocs

## Customization

### PROJECT_BRIEF.md

Each project should have a `PROJECT_BRIEF.md` that describes:
- What you're building
- Key constraints and requirements
- Domain-specific terminology

See `templates/PROJECT_BRIEF.md` for the template.

### Overriding Defaults

Create a `.agents/overrides.md` to customize agent behavior:

```markdown
# Project Overrides

## Additional Context
- This is a healthcare app requiring HIPAA compliance

## Modified Rules
- Use `pnpm` instead of `bun` (legacy constraint)
```

## Contributing

To add a new recipe:

1. Create a new directory under `prompts/`
2. Follow the structure above
3. Ensure AGENTS.md works with all major AI tools
4. Test with a real project before committing
