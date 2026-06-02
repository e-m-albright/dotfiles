---
name: project-files
description: Conventions for justfiles, .gitignore, README.md, and .env.example — default help recipe, section ordering, confirm gates, gitignore grouping, and minimal README template. Use when creating or editing a justfile, .gitignore, README, or .env.example; adding a new `just` recipe; deciding what to gitignore; scaffolding a new project's common files; or when the user says "set up the justfile", "what goes in .gitignore", "add a recipe", "write a README".
---

# Project Files

## Justfile Conventions

**Default command** is always a colorized help listing — not `just --list`:

```just
# Show all available commands
@default:
    just --list --unsorted --list-heading $'\e[1;34m Available Commands:\e[0m\n'
```

**Section organization** — group recipes under comment headers:

```
Development → Quality → Testing → Database → Dependencies → Git Hooks → Utilities → Deployment
```

**Naming patterns:**
- `dev`, `build`, `run` — primary actions
- `test`, `test-cov`, `test-watch`, `test-filter` — testing variants
- `lint`, `format`, `typecheck`, `check` — quality (check = all)
- `db-migrate`, `db-rollback`, `db-new`, `db-shell` — database
- `hooks-install`, `hooks-run` — git hooks
- `ci` — runs all checks (what CI would run)
- `clean`, `clean-all` — cleanup (clean-all includes deps/venv)

**Confirm gate** — any command that alters production or destroys data:

```just
[confirm("⚠ This will reset the database. Continue? [y/N]")]
db-reset:
    # ...

[confirm("⚠ This will deploy to production. Continue? [y/N]")]
deploy-prod:
    # ...
```

Commands that must have confirm gates:
- `db-reset`, `db-rollback` (on prod)
- `deploy-*` (any deployment)
- `clean-all` (removes deps)
- Any `--force` or destructive operation

**Variables** at the top for project-specific values:

```just
binary := "myapp"
port := "8000"
```

**Recipe comments** — every recipe gets a doc comment (shown in `--list`):

```just
# Run tests with coverage report
test-cov:
```

## .gitignore

**Structure** — group by category with section comments:

```gitignore
# Dependencies
node_modules/

# Build output
dist/
build/

# Environment
.env
.env.local
!.env.example

# Testing & coverage
coverage/
.pytest_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store

# AI tools
.agents/
ai/.agents/plans/
ai/.agents/research/
.cursor/rules/
```

**Key rules:**
- Always gitignore `.env` but keep `.env.example`
- Gitignore `.agents/` at repo root; in dotfiles, use `ai/.agents/` subdirs for ephemeral work
- Commit `.ai/rules/` (all rules are copied, not symlinked)
- Gitignore `.cursor/rules/` (auto-generated symlinks to `.ai/rules/`)

## README.md

**Minimal template** — fill in as the project grows:

```markdown
# Project Name

One-line description.

## Quick Start

\`\`\`bash
just install
just dev
\`\`\`

## Commands

Run `just` to see all available commands.
```

Don't over-document upfront. Let the README grow with the project.

## .env.example

- Include every env var the app needs with placeholder values
- Group by category (app, database, auth, external services)
- Add comments explaining non-obvious vars
- Never include real secrets — use descriptive placeholders

_Promoted from `.ai/rules/process/project-files.mdc` (was an always-on rule; now an on-demand skill)._
