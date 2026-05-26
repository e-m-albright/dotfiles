# Developer Workflow Guide

**Philosophy**: Your tools should disappear. The best setup is one where you think about the problem, not the toolchain. Every tool here earns its place by reducing friction or catching mistakes automatically.

> **This guide covers**: How all the tools in this dotfiles repo work together — from starting a new project to shipping code. It's the manual for the machine.

---

## The Stack at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                        You                                  │
├──────────────┬──────────────┬───────────────────────────────┤
│  Claude Code │    Cursor    │       Ghostty                  │
│  (agentic)   │  (IDE)       │  (terminal)                    │
├──────────────┴──────────────┴───────────────────────────────┤
│  Superpowers Skills · Plugins · MCP Servers · Hooks         │
├─────────────────────────────────────────────────────────────┤
│  just · lefthook · uv/bun/cargo/go · ruff/biome · ty/tsc   │
├─────────────────────────────────────────────────────────────┤
│  git · gh · delta · Linear · Granola · Obsidian             │
├─────────────────────────────────────────────────────────────┤
│  Railway · Cloudflare · Supabase                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool Reference

### AI Coding Tools

| Tool | What It Does | When to Use |
|------|-------------|-------------|
| **Claude Code** | Agentic CLI — reads/writes files, runs commands, uses MCP servers | Complex multi-file tasks, architecture, refactoring, long-running autonomous work |
| **Cursor** | AI-native IDE (VS Code fork) with inline completions and chat | Rapid iteration, debugging, single-file edits, visual diffs |
| **Ghostty** | Fast native terminal emulator | Running Claude Code sessions with tabs/splits. |

**General rule**: Claude Code for depth, Cursor for speed.

### The `dotfiles` CLI

Your entry point for managing this entire setup:

```bash
dotfiles install        # Full setup from scratch
dotfiles doctor         # Health check — tools, symlinks, configs (--fix to repair)
dotfiles update         # Update everything — brew, runtimes, tools, npm globals
dotfiles stale          # Find disabled packages still installed + broken symlinks
dotfiles scaffold       # Create a new project with AI rules and templates
dotfiles agent-setup   # Re-deploy Claude Code config (plugins, hooks, MCP, skills)
dotfiles agents         # Show active MCP servers, hooks, skills across Claude + Cursor
dotfiles brew           # Re-run Homebrew setup
dotfiles dock           # Reset macOS Dock layout
dotfiles clean          # Prune Homebrew caches (30-day)
```

Run `dotfiles doctor` regularly. It checks: core tools, editors, runtimes, AI tools, dev tools, config symlinks, git identity, Claude plugins/hooks/MCP, and Ghostty.

### Task Runner: Just

Every project gets a `justfile`. Common commands across all stacks:

```bash
just              # List all commands
just check        # Run lint + typecheck + test
just lint         # Lint only
just format       # Format only
just typecheck    # Type check only
just test         # Run tests
just test-cov     # Tests with coverage
just ci           # Full CI pipeline locally
just clean        # Remove caches and build artifacts
just hooks-install  # Install git hooks
```

### Git Hooks: Lefthook

Hooks run automatically on commit and push. You never invoke these directly:

- **pre-commit**: Lint, format, and type-check staged files (parallel)
- **pre-push**: Run tests
- **commit-msg**: Validate conventional commit format (TypeScript projects)

Skip hooks in emergencies: `LEFTHOOK=0 git commit` or `--no-verify`.

### Git Workflow

Key config choices already made for you:

- **Pull**: rebase (not merge)
- **Push**: auto-setup remote tracking
- **Diffs**: delta with side-by-side Dracula theme
- **Merge conflicts**: zdiff3 style (shows base + both sides)
- **Rerere**: enabled — Git remembers how you resolved conflicts
- **SSH**: Auto-rewrites HTTPS GitHub/GitLab URLs to SSH

Useful aliases (all in `.gitconfig`):

```bash
git s              # status --short
git l              # Pretty one-line log
git d / git ds     # Diff / diff staged
git undo           # Soft reset last commit
git unstage        # Unstage everything
git fixup <sha>    # Create a fixup commit
git ri <n>         # Interactive rebase last n commits
git clean-branches # Delete merged local branches
git recent         # Show recent branches
git who            # Shortlog by author
```

---

## Starting a New Project

### 1. Scaffold

```bash
dotfiles scaffold
```

This walks you through selecting a recipe (typescript, python, golang, rust) and app type (e.g., svelte, fastapi, cli, axum). It creates:

| File/Dir | Purpose |
|----------|---------|
| `AGENTS.md` | Project-level AI instructions (customize this) |
| `.ai/rules/*.mdc` | Universal rules (synced from dotfiles) + stack-specific rules |
| `.cursor/rules/*.mdc` | Symlinks to `.ai/rules/` |
| `.agents/` | Working directory for AI artifacts (plans, research, decisions) |
| `justfile` | Task runner commands |
| `lefthook.yml` | Git hooks config |
| `.gitignore` | Language-appropriate ignores |
| `.env.example` | Environment variable template |
| Template configs | biome.json, pyproject.toml, Cargo.toml, etc. |

### 2. Customize AGENTS.md

The scaffolded `AGENTS.md` is a starting point. Edit it to describe:
- What this project does
- Key architectural decisions
- Team conventions that differ from defaults

### 3. Install Dependencies and Hooks

```bash
just install-dev     # Install dependencies
just hooks-install   # Set up git hooks
```

---

## The AI-Assisted Development Loop

### Superpowers Workflow

The superpowers plugin provides a structured pipeline for feature development. You don't have to use every step, but the full flow is:

```
 /brainstorm  →  /write-plan  →  /worktree  →  /execute-plan  →  /request-review  →  /finish-branch
     │               │              │               │                   │                   │
  Explore         Break into      Isolate         Execute            Review             Merge &
  requirements    tasks with      on a new        in batches         against            clean up
  & design        file paths      branch          with checkpoints   spec
```

#### When to Use Each Skill

| Skill | Trigger | What Happens |
|-------|---------|-------------|
| `/brainstorm` | Before any non-trivial feature | Socratic Q&A to refine requirements, explores alternatives, saves design doc |
| `/write-plan` | After design is approved | Breaks work into 2-5 minute tasks with exact file paths and code snippets |
| `/worktree` | Before starting implementation | Creates isolated git worktree on a new branch |
| `/execute-plan` | When plan is ready | Runs tasks in batches, pauses for human review between batches |
| `/subagent-dev` | For parallel implementation | Dispatches independent tasks to subagents with two-stage review |
| `/dispatch` | For any parallel work | Spawns subagents for independent queries or tasks |
| `/debug` | When something breaks | 4-phase: reproduce → hypothesize → investigate → fix |
| `/tdd` | When writing new logic | Red-green-refactor cycles |
| `/request-review` | Before merging | Agent reviews changes against spec |
| `/receive-review` | After getting feedback | Structured process for addressing review comments |
| `/finish-branch` | After review passes | Merge, clean up worktree, prune branches |

**Shortcut for small tasks**: Skip straight to implementation. Superpowers detects when work is trivial and won't force you through the full pipeline.

### Other Useful Skills

| Skill | What It Does |
|-------|-------------|
| `/commit` | Stage, generate message, commit |
| `/commit-push-pr` | Commit + push + open PR |
| `/review-pr` | Comprehensive PR review with specialized agents |
| `/scaffold` | Run the project scaffolder |
| `/doctor` | Run dotfiles doctor |
| `/agents-overview` | Show all active MCP, hooks, skills |

### Plugins Working in the Background

These activate automatically — you don't invoke them:

| Plugin | What It Does |
|--------|-------------|
| **ty-lsp / typescript-lsp / rust-analyzer-lsp** | In-session type checking and diagnostics |
| **explanatory-output-style** | Adds educational insights to responses |
| **security-guidance** | Flags security concerns in generated code |
| **context7** | Fetches up-to-date library docs (say "use context7" to trigger) |
| **format-on-save hook** | Auto-formats after every file edit (Biome/Ruff/rustfmt/gofmt) |
| **verification-before-completion** | Agent runs tests/builds before claiming done |

### MCP Integrations

Claude Code and Cursor connect to external services via MCP:

| Server | What You Can Do |
|--------|----------------|
| **GitHub** | Create PRs, read issues, search code, manage releases |
| **Linear** | Create/update issues, manage projects, read comments |
| **Notion** | Search pages, create/update content |
| **Granola** | Search meeting notes, pull transcripts (Claude only) |
| **Context7** | Fetch versioned library documentation |

Example usage in Claude Code:
```
"Check Linear for open bugs in the INGEST project"
"Find my last meeting notes about the auth redesign"
"Look up the SvelteKit docs for form actions using context7"
```

---

## Stack-Specific Workflows

### Python

```bash
uv sync --dev          # Install deps
uv run ty check        # Type check (Astral's ty)
uv run ruff check .    # Lint
uv run ruff format .   # Format
uv run pytest          # Test
just check             # All of the above
```

Key decisions: UV (not pip), Ruff (not Black+isort), ty (not Pyright/mypy), Python 3.14.

### TypeScript

```bash
bun install            # Install deps
bun run check          # Type check + lint
bunx biome check .     # Lint + format
bun test               # Test
just check             # All of the above
```

Key decisions: Bun (not npm), Biome (not ESLint+Prettier), SvelteKit 2, Tailwind v4.

### Go

```bash
go build ./...                  # Build
golangci-lint run               # Lint (aggregates 50+ linters)
go test ./...                   # Test
just check                      # All of the above
```

Key decisions: Go 1.25+, chi/v5, sqlc, pgx/v5, Atlas for migrations.

### Rust

```bash
cargo build            # Build
cargo clippy           # Lint
cargo fmt              # Format
cargo test             # Test
just check             # All of the above
```

Key decisions: Stable toolchain, Axum, Tokio, SQLx.

---

## Hooks & Automation

### Claude Code Hooks (in `agents/claude/hooks.json`)

| Event | What Happens |
|-------|-------------|
| **PreToolUse** (Edit/Write) | Blocks edits to SSH keys and credential files |
| **PostToolUse** (Edit/Write) | Auto-formats the edited file with the project's formatter |
| **Stop** | macOS notification "Done — ready for input" |
| **Notification** (permission_prompt) | macOS alert sound when Claude needs approval |

### Cursor Hooks

| Event | What Happens |
|-------|-------------|
| **afterFileEdit** | Format-on-save (same formatter as Claude) |
| **beforeShellExecution** | Guards against destructive commands (rm -rf, git reset --hard, sudo) |

---

## Daily Practices

### Morning

```bash
dotfiles update        # Keep tools current
dotfiles doctor        # Catch drift early
```

### Starting a Feature

1. Open a terminal
2. `/brainstorm` with Claude Code to explore the problem
3. `/write-plan` to break it into tasks
4. `/worktree` to isolate the work (or just branch if small)
5. Implement — use `/tdd` for logic-heavy work, `/execute-plan` for planned work
6. `/commit` as you go

### Shipping

1. `just check` — make sure everything passes locally
2. `/request-review` — let Claude review against the spec
3. `/commit-push-pr` — or use `gh pr create` directly
4. Link the Linear ticket in the PR description

### Debugging

1. **Don't guess.** Use `/debug` — it enforces: reproduce → hypothesize → investigate → fix
2. If it's a type error, check `ty` / `tsc` output first
3. If it's a runtime error, reproduce with a minimal test case

---

## Customization

### Writing Custom Skills

Skills live in `agents/claude/skills/` and get deployed to `~/.claude/skills/`. Format:

```markdown
---
name: my-skill
description: When to trigger this skill (trigger conditions, not workflow summary)
---

## Workflow
1. Step one
2. Step two
```

Use `/write-skill` (from superpowers) to create new skills with TDD — it watches an agent fail without the skill first, then writes the skill to fix the gap.

**Priority**: Project skills (`.claude/skills/`) > Personal skills (`~/.claude/skills/`) > Plugin skills.

### Adding Rules

Rules live in `.ai/rules/` with `.mdc` extension and YAML frontmatter:

```markdown
---
description: When this rule applies
globs: "**/*.py"        # optional: file-pattern trigger
alwaysApply: false      # true = always loaded into context
---

# Rule content here
```

Universal rules go in `.ai/rules/process/`. Stack-specific rules go in `languages/`, `tooling/`, or `frameworks/`.

### Adding MCP Servers

Edit `agents/shared/mcp-servers.json` and specify targets:

```json
{
  "my-server": {
    "command": "npx",
    "args": ["-y", "my-mcp-server"],
    "targets": ["claude", "cursor"]
  }
}
```

Then run `dotfiles agent-setup` to deploy.

### Modifying Hooks

Edit `agents/claude/hooks.json` directly, then run `dotfiles agent-setup`.

---

## Code Review: Fix-First

Our review rules (`.ai/rules/process/code-review.mdc`) use a **fix-first classification** inspired by gstack. Every review finding gets classified before reporting:

| Classification | Action | Example |
|---------------|--------|---------|
| **AUTO-FIX** | Fix silently | Unused imports, missing type annotations, formatting |
| **ASK** | Report with recommendation | Architecture changes, security decisions, API surface |

This reduces noise dramatically. Instead of a 20-item list where 15 are mechanical, you get the 15 fixed silently and a focused 5-item list of things that actually need judgment.

The review also evaluates five dimensions: **Correctness**, **Security**, **API quality**, **Maintainability**, **Testing**. Not personas — explicit checklists of what to look for in each dimension. See the full rule for details.

## Testing the Scaffold

```bash
dotfiles test              # Full eval (all 3 tiers)
dotfiles test --quick      # Static validation + consistency only
```

The eval framework (`tests/test_scaffold.sh`) validates our scaffolding at three tiers:

1. **Static validation** — Rule files have valid frontmatter, templates parse (TOML, YAML, JSON), referenced tools exist on the system
2. **Consistency checks** — Rules agree across files (e.g., Python type checker is `ty` everywhere, not `pyright` in some files and `ty` in others), LSP plugins match tool choices
3. **Scaffold output validation** — Actually runs `scaffold.sh` for every recipe/app-type combo and checks: required files exist, symlinks aren't broken, templates use correct tools, re-runs are idempotent

Run this after changing any rule, template, or scaffold logic.

## Patterns Worth Knowing

### Design Principles (from gstack and our own experience)

- **Encode criteria, not personas.** "Act as a security engineer" is theater. Listing the actual checks (SQL injection, XSS, auth bypass, path traversal) changes behavior. Our `code-review.mdc` uses explicit checklists, not role-playing.
- **Bisectable commits** — Order commits by dependency: infrastructure → models → controllers → tests. Each commit should be independently valid.

### From Superpowers

- **Skills are composable** — Chain them: brainstorm → plan → worktree → execute → review → finish
- **Override anything** — Place a SKILL.md with the same name in `.claude/skills/` to override plugin behavior for a specific project
- **Descriptions are triggers** — Keep skill descriptions focused on WHEN to trigger, not WHAT the workflow does. Claude reads the description to decide whether to invoke.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Claude Code doesn't have my plugins | Run `dotfiles agent-setup` |
| Hooks aren't running | `just hooks-install` or `lefthook install` |
| Type checker not found | `uv sync --dev` (Python) or `bun install` (TS) |
| Format-on-save not working | Check `dotfiles doctor` — formatter must be installed |
| MCP server not connecting | Check `dotfiles agents` for status |
| Stale packages installed | Run `dotfiles stale` to find them |
