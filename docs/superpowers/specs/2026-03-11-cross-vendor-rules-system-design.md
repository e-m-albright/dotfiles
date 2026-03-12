# Cross-Vendor Rules System

**Created**: 2026-03-11
**Status**: Approved
**Author**: @evan + Claude

## Summary

Restructure the dotfiles prompt/scaffolding system from encyclopedic per-language docs into a lean, cross-vendor rules system. AGENTS.md becomes a ~30-line pointer + project context. All technical guidance moves to `.ai/rules/` as short, decisive `.mdc` files that work with Claude Code, Cursor, and Gemini CLI.

## Problem

The current system has:
- **1,285+ lines per language** across 3-5 files (BASE, STYLE, STACK, FRAMEWORK) with massive duplication
- **Code examples LLMs already know** (how to write a FastAPI route, Pydantic model, Drizzle query)
- **STACK.md and STYLE.md never scaffolded** — orphaned from the pipeline
- **Shared docs (2,254 lines) never deployed** to projects
- **Overlap** between cursor rules, AGENTS.md content, and superpowers plugin
- **Cursor-only** rule format — Claude Code and Gemini can't discover `.cursor/rules/`

## Design

### 1. Canonical Rules Directory: `.ai/rules/`

All guidance lives as `.mdc` files (markdown + YAML frontmatter). This format is native to Cursor and readable by Claude Code and Gemini (they ignore the frontmatter).

```
dotfiles/.ai/rules/
├── process/                    # HOW to work (universal)
│   ├── global-process.mdc
│   ├── style-principles.mdc
│   ├── git-workflow.mdc
│   ├── tickets-and-prs.mdc
│   ├── agent-artifacts.mdc
│   └── shell-automation.mdc
├── languages/                  # Language ergonomics & conventions
│   ├── typescript.mdc
│   ├── python.mdc
│   ├── golang.mdc
│   └── rust.mdc
├── frameworks/                 # Framework-specific patterns
│   ├── sveltekit.mdc
│   ├── astro.mdc
│   ├── fastapi.mdc
│   ├── chi.mdc
│   ├── axum.mdc
│   └── tauri.mdc
└── tooling/                    # Stack decisions & tool choices
    ├── stack-typescript.mdc
    ├── stack-python.mdc
    ├── stack-golang.mdc
    ├── stack-rust.mdc
    └── services.mdc
```

### 2. Reference Guides (Not Deployed)

Deeper reference docs stay in dotfiles, not scaffolded into projects:

```
dotfiles/prompts/guides/
├── ai-tools.md
├── infrastructure.md
├── services.md
├── customer-discovery.md
├── project-memory.md
└── agent-output.md
```

### 3. Selective Deployment via scaffold.sh

scaffold.sh symlinks only relevant rules per recipe + app-type:

**Universal (all projects):**
- `process/global-process.mdc`
- `process/style-principles.mdc`
- `process/git-workflow.mdc`
- `process/tickets-and-prs.mdc`
- `process/agent-artifacts.mdc`

**Per recipe:**

| Recipe | Additional Rules |
|--------|-----------------|
| `typescript svelte` | `languages/typescript.mdc`, `frameworks/sveltekit.mdc`, `tooling/stack-typescript.mdc` |
| `typescript astro` | `languages/typescript.mdc`, `frameworks/astro.mdc`, `tooling/stack-typescript.mdc` |
| `python fastapi` | `languages/python.mdc`, `frameworks/fastapi.mdc`, `tooling/stack-python.mdc`, `process/shell-automation.mdc` |
| `golang chi` | `languages/golang.mdc`, `frameworks/chi.mdc`, `tooling/stack-golang.mdc`, `process/shell-automation.mdc` |
| `rust axum` | `languages/rust.mdc`, `frameworks/axum.mdc`, `tooling/stack-rust.mdc`, `process/shell-automation.mdc` |
| `rust tauri` | `languages/rust.mdc`, `frameworks/tauri.mdc`, `tooling/stack-rust.mdc`, `process/shell-automation.mdc` |

**In the scaffolded project:**

```
my-project/
├── AGENTS.md                        # ~30 lines: pointers + project context
├── .ai/rules/                       # Symlinked (selective, auto-updates)
│   ├── global-process.mdc           → ~/dotfiles/.ai/rules/process/...
│   ├── style-principles.mdc         → ~/dotfiles/.ai/rules/process/...
│   ├── git-workflow.mdc             → ~/dotfiles/.ai/rules/process/...
│   ├── tickets-and-prs.mdc          → ~/dotfiles/.ai/rules/process/...
│   ├── agent-artifacts.mdc          → ~/dotfiles/.ai/rules/process/...
│   ├── python.mdc                   → ~/dotfiles/.ai/rules/languages/...
│   ├── fastapi.mdc                  → ~/dotfiles/.ai/rules/frameworks/...
│   └── stack-python.mdc             → ~/dotfiles/.ai/rules/tooling/...
├── .cursor/rules/                   # Symlinks to .ai/rules/ for Cursor
│   ├── global-process.mdc           → ../.ai/rules/global-process.mdc
│   ├── python.mdc                   → ../.ai/rules/python.mdc
│   └── ...
└── .agents/                         # Working files (unchanged)
```

### 4. Lean AGENTS.md Template

```markdown
# AGENTS.md

Read all `.ai/rules/*.mdc` files for coding conventions, stack decisions,
and process rules. Cursor users: rules are also in `.cursor/rules/`.

---

## Research & Library Usage

**Check the current date before researching.** Your training data may be stale.
When using a library, search for latest docs first. Verify you're using
the current API, not a deprecated one.

---

## Project Context

<!-- Fill this in -->

### Overview
<!-- What does this project do? Who is it for? -->

### Goals
- [ ] Goal 1

### Non-Goals
- Not building X

### Technical Constraints
- Deployment target: [platform]

### Domain Context
<!-- Key terms, business rules, entities -->
```

### 5. Rule File Design Principles

Each rule file is **short, decisive, and actionable**:

- **~50-80 lines** per file (not 300-600)
- **Decisions, not tutorials** — "Use X, avoid Y" not "here's how to write a Pydantic model"
- **Critical deviations only** — things the LLM would get wrong without guidance
- **Always/Never/Ask First** sections for clear guardrails
- **No duplicate content** across files
- **`.mdc` format** with YAML frontmatter for Cursor compatibility

Example structure:
```
---
description: [what this rule covers]
globs: "[file patterns]" (optional)
alwaysApply: [true/false]
---

# Title

## [Category]
- Concise directive
- Concise directive

## Always
- ...

## Never
- ...
```

### 6. Content Transformation

Each recipe's 3-5 files (800-1,200+ lines) condense to 3 rule files (~190 lines):

| Current File | Lines | Becomes | Lines |
|-------------|-------|---------|-------|
| `python/BASE.md` | 296 | `languages/python.mdc` | ~50 |
| `python/STYLE.md` | 561 | *(deleted — conventions enforced by Ruff config)* | 0 |
| `python/STACK.md` | 428 | `tooling/stack-python.mdc` | ~80 |
| `python/fastapi/FRAMEWORK.md` | 342 | `frameworks/fastapi.mdc` | ~60 |
| **Total** | **1,627** | **3 files** | **~190** |

Same pattern for TypeScript, Go, Rust.

### 7. Cross-Vendor Discovery

| Tool | How It Discovers Rules |
|------|----------------------|
| **Claude Code** | AGENTS.md says "read `.ai/rules/*.mdc`" → Claude reads them |
| **Cursor** | `.cursor/rules/*.mdc` symlinks → auto-discovered by Cursor |
| **Gemini CLI** | AGENTS.md says "read `.ai/rules/*.mdc`" → Gemini reads them |

### 8. Migration from Current System

**Files to create:**
- `.ai/rules/process/` — transform existing `.cursor/rules/` content + `STYLE_PRINCIPLES.md`
- `.ai/rules/languages/` — distill from each recipe's `BASE.md` + `STYLE.md`
- `.ai/rules/frameworks/` — distill from each recipe's `FRAMEWORK.md`
- `.ai/rules/tooling/` — distill from each recipe's `STACK.md` + shared `SERVICES.md`

**Files to move:**
- `prompts/shared/AI_TOOLS.md` → `prompts/guides/ai-tools.md`
- `prompts/shared/INFRASTRUCTURE.md` → `prompts/guides/infrastructure.md`
- `prompts/shared/SERVICES.md` → `prompts/guides/services.md`
- `prompts/shared/CUSTOMER_DISCOVERY.md` → `prompts/guides/customer-discovery.md`
- `prompts/shared/PROJECT_MEMORY.md` → `prompts/guides/project-memory.md`
- `prompts/shared/AGENT_OUTPUT.md` → `prompts/guides/agent-output.md`

**Files to delete:**
- `prompts/python/AGENTS.md` (project-specific GEO file, not a template)
- `prompts/shared/AGENTS_HEADER.md` (replaced by lean template in scaffold.sh)
- All `*/STYLE.md` files (conventions enforced by linter configs)
- All `*/BASE.md` files (content distilled into rule files)
- All `*/STACK.md` files (content distilled into tooling rules)
- All `*/FRAMEWORK.md` files (content distilled into framework rules)

**Files to update:**
- `prompts/scaffold.sh` — new deployment logic
- `AGENTS.md` (dotfiles repo) — update pointers
- `README.md` — reflect new structure

### 9. Superpowers Compatibility

This system is designed to work standalone but benefit from superpowers when present:

- **Standalone:** Rules provide full technical guidance. `.agents/` structure is documented in `agent-artifacts.mdc`.
- **With superpowers:** Process rules (global-process, git-workflow, agent-artifacts) provide baseline that superpowers enhances with deeper workflow automation (TDD cycles, brainstorming, plan execution).
- **No conflict:** Rules cover domain/stack decisions. Superpowers covers development process. Orthogonal concerns.

### 10. Future: Skills Directory

The `.ai/rules/` directory can grow into a richer skills library over time. Potential additions:

- `skills/testing-strategies.mdc` — when to unit test vs integration test vs e2e
- `skills/api-design.mdc` — REST conventions, error formats, pagination
- `skills/database-patterns.mdc` — migrations, indexing, N+1 prevention
- `skills/deployment.mdc` — Railway/Cloudflare/Fly.io patterns
- `skills/security.mdc` — OWASP top 10 prevention patterns
- `skills/performance.mdc` — profiling, caching, lazy loading

These would follow the same format and selective deployment model.
