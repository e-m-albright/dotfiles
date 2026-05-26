# Project Scaffolding

Seed new or existing projects with cross-vendor AI rules that work with Claude Code, Cursor, and Gemini CLI.

**Philosophy**: Dotfiles seeds and influences. Projects own themselves.

## Usage

One script, idempotent -- run it on new or existing projects:

```bash
# Create new projects
~/dotfiles/prompts/scaffold.sh typescript my-app           # SvelteKit (default)
~/dotfiles/prompts/scaffold.sh typescript astro my-blog    # Astro
~/dotfiles/prompts/scaffold.sh python my-api               # FastAPI (default)
~/dotfiles/prompts/scaffold.sh golang my-service           # Chi (default)
~/dotfiles/prompts/scaffold.sh rust my-service             # Axum (default)
~/dotfiles/prompts/scaffold.sh rust tauri my-desktop-app   # Tauri

# Seed existing projects (use . for current directory)
~/dotfiles/prompts/scaffold.sh typescript .
~/dotfiles/prompts/scaffold.sh python ~/code/my-api

# Force regenerate everything (including AGENTS.md)
~/dotfiles/prompts/scaffold.sh --force python .
```

Safe to run multiple times -- only adds missing pieces.

### What Gets Created

| File/Directory | Purpose | Ownership |
|----------------|---------|-----------|
| `AGENTS.md` | ~30-line pointer + project context | Project-owned (edit freely) |
| `.ai/rules/*.mdc` | AI rules (process, language, framework, stack) | Universal = symlinked, Recipe = copied |
| `.cursor/rules/*.mdc` | Cursor symlinks → `.ai/rules/` | Auto-generated |
| `.agents/` | Working files: plans, research, sessions (gitignored) | Project-owned |
| `.agents/decisions/` | Architecture Decision Records (versioned) | Project-owned |

### How Rules Deploy

- **Universal rules** (process, style, workflow) are **symlinked** — auto-update from dotfiles
- **Recipe rules** (language, framework, stack) are **copied** — project can customize
- **Cursor symlinks** are auto-generated relative links to `.ai/rules/`
- Only rules relevant to the recipe are deployed, not the entire library

### On Re-run

- **AGENTS.md** -- NOT overwritten (project owns it). Use `--force` to regenerate.
- **Universal rules** -- re-symlinked (always up to date from dotfiles).
- **Recipe rules** -- skip existing files (project may have customized).
- **Cursor symlinks** -- refreshed to match `.ai/rules/`.

---

## Available Recipes

| Recipe | App Type | Stack | Use Case |
|--------|----------|-------|----------|
| `typescript` | `svelte` (default) | Bun + SvelteKit 2 + Svelte 5 | Full-stack apps |
| `typescript` | `astro` | Bun + Astro | Content sites, blogs |
| `python` | `fastapi` (default) | UV + FastAPI + SQLAlchemy | APIs, AI services |
| `golang` | `chi` (default) | Go 1.25+ Chi router + sqlc | APIs, services |
| `rust` | `axum` (default) | Tokio + Axum + SQLx | High-perf APIs, systems |
| `rust` | `tauri` | Tauri 2 + SvelteKit | Desktop apps |

---

## AI Rules Library

All guidance lives in `dotfiles/.ai/rules/` as `.mdc` files (markdown + YAML frontmatter):

```
.ai/rules/
├── process/        # Universal: safety, style, git workflow, shell scripts
├── languages/      # Language ergonomics: TypeScript, Python, Go, Rust
├── frameworks/     # Framework patterns: SvelteKit, Astro, FastAPI, Chi, Axum, Tauri
└── tooling/        # Stack decisions: Pick/Avoid tables per language + cloud services
```

Each file is **~50-80 lines**, focused on **decisions, not tutorials**. Things the LLM would get wrong without guidance.

---

## Reference Guides

Deeper reference docs in `prompts/guides/` (not deployed to projects):

| Guide | Contents |
|-------|----------|
| `ai-tools.md` | AI development workflow and tools |
| `services.md` | Cloud services (hosting, database, auth, etc.) |
| `infrastructure.md` | Docker, Pulumi, observability |
| `customer-discovery.md` | Customer interview methodology |
| `project-memory.md` | Decision organization system |
| `ml-python.md` | Python ML/data science patterns |

---

## Philosophy

- **One pick per category** -- No "it depends." Every choice is justified.
- **Start minimal** -- Add tools when you need them, not before.
- **Projects own themselves** -- Dotfiles seeds good defaults; projects can diverge.
- **Cross-vendor** -- Works with Claude Code, Cursor, and Gemini CLI.
