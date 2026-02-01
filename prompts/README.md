# Prompts

Opinionated recipe book for bootstrapping new projects with best-in-class tech stacks.

Each recipe is a complete, production-ready configuration that can be used to:
1. **Seed a new project** with optimal defaults
2. **Bring existing projects into compliance** with modern standards
3. **Guide AI coding agents** with consistent, high-quality instructions

## Philosophy

- **One pick per category** — No "it depends." Every choice is justified.
- **Agent-first** — All configs work with Claude, Cursor, Gemini, ChatGPT.
- **Human-readable** — Every file is organized, commented, and skimmable.
- **DX-optimized** — Fast feedback loops, minimal config, maximum productivity.

## Available Recipes

| Recipe | Runtime | Framework | Use Case |
|--------|---------|-----------|----------|
| [typescript](./typescript/) | Bun | SvelteKit 2 + Svelte 5 | Full-stack web apps |
| [python](./python/) | UV | FastAPI + Pydantic | APIs, ML services |
| [golang](./golang/) | Go 1.22+ | stdlib + sqlc | High-perf services |

## Recipe Structure

Each recipe contains:

```
recipe-name/
├── STACK.md              # Tech stack decisions + rationale
├── AGENTS.md             # Cross-platform agent instructions (symlink this)
├── STYLE.md              # Code style guide
├── skills/               # Agent skills for specific tools/frameworks
│   ├── SKILL.md          # Main skill definition
│   └── references/       # Supporting documentation
├── templates/            # Starter files
│   ├── .gitignore
│   ├── justfile
│   ├── biome.json        # (TypeScript)
│   ├── pyproject.toml    # (Python)
│   └── ...
└── hooks/                # Git hooks (lefthook config)
```

## Quick Start

### New Project

```bash
# From your dotfiles
./prompts/init.sh typescript my-new-app

# Or manually
mkdir my-new-app && cd my-new-app
cp -r ~/dotfiles/prompts/typescript/templates/* .
ln -s ~/dotfiles/prompts/typescript/AGENTS.md ./AGENTS.md
```

### Existing Project

```bash
# Copy the AGENTS.md to your project root
cp ~/dotfiles/prompts/typescript/AGENTS.md ./AGENTS.md

# Copy specific configs as needed
cp ~/dotfiles/prompts/typescript/templates/biome.json .
cp ~/dotfiles/prompts/typescript/templates/.gitignore .
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
# Or reference it in your system prompt
```

## Project Organization

All recipes instruct agents to organize their output in `.agents/`:

```
your-project/
├── .agents/              # Agent-generated artifacts (gitignored by default)
│   ├── plans/            # Implementation plans
│   ├── research/         # Investigation notes
│   ├── scratch/          # Temporary work files
│   └── sessions/         # Conversation logs (optional)
├── AGENTS.md             # Agent instructions (symlinked from recipe)
├── PROJECT_BRIEF.md      # Your project-specific context (you write this)
└── ...                   # Your actual code
```

## Customization

### PROJECT_BRIEF.md

Each project should have a `PROJECT_BRIEF.md` that describes:
- What you're building
- Key constraints and requirements
- Domain-specific terminology
- Integration points

See `templates/PROJECT_BRIEF.md` for the template.

### Overriding Defaults

Create a `.agents/overrides.md` to customize agent behavior per-project:

```markdown
# Project Overrides

## Additional Context
- This is a healthcare app requiring HIPAA compliance
- All dates must be ISO 8601 format

## Modified Rules
- Use `pnpm` instead of `bun` (legacy constraint)
```

## Contributing

To add a new recipe:

1. Create a new directory under `prompts/`
2. Follow the structure above
3. Ensure AGENTS.md works with all major AI tools
4. Test with a real project before committing
