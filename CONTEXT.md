# Repository Context

Glossary for the agentic-tooling vocabulary used in this dotfiles repo. Distinct concepts that look similar from a distance — disambiguating them up front saves churn.

## Language

**Skill**:
A capability triggered by description match, loaded progressively. Lives at `.ai/skills/<name>/SKILL.md` (canonical) and is symlinked into `agents/<vendor>/skills/<name>`. Its frontmatter `description` is the only trigger surface — see `.ai/skills/skill-creator/references/skill-format.md`.
_Avoid_: command, prompt.

**Agent** (subagent):
A worker dispatched via the `Agent` tool with isolated context. Lives at `.ai/agents/<name>.md` (canonical) and is symlinked into `agents/<vendor>/agents/<name>.md`. Different frontmatter format from skills (`tools` is comma-separated; no `allowed-tools`). See `.ai/skills/skill-creator/references/agent-format.md`.
_Avoid_: assistant, helper, model.

**Rule**:
A persistent guideline loaded into the session at startup or on glob match. Lives at `.ai/rules/<category>/<name>.mdc` with frontmatter `globs:` controlling when it loads. Doesn't trigger; just ambient context.
_Avoid_: convention, policy (use these in prose, but the artifact name is "rule").

**Hook**:
A shell command that the harness executes in response to a tool-use event (`PreToolUse`, `PostToolUse`, `Stop`, `Notification`). Configured in `agents/<vendor>/hooks.json`. Runs outside Claude's awareness — exit code 2 blocks the action.
_Avoid_: trigger, listener.

**MCP server**:
An external process exposing tools/resources/prompts via the Model Context Protocol. Configured in `agents/shared/mcp-servers.json`. Loaded per session; consumes context window.
_Avoid_: tool provider, plugin (those mean other things here).

**Plugin**:
A bundle of skills + agents + commands distributable via Claude Code's `/plugin install` mechanism. Listed in `.claude-plugin/marketplace.json` at repo root.
_Avoid_: package, extension.

**Slash command**:
A skill or workflow invocable via `/<name>` in the harness. We don't ship custom slash commands today — they are conceptually subsumed by skills with `disable-model-invocation: true`.

## Relationships

- A **plugin** bundles **skills**, **agents**, and slash commands.
- A **skill** is described by its frontmatter and triggers in response to user phrases / contexts.
- An **agent** is dispatched by another agent (via the `Agent` tool) with a focused task.
- **Rules** load ambient guidance; **hooks** intercept tool calls; **MCP servers** add new tools.
- **Skills** and **agents** in this repo are canonicalized in `.ai/` and symlinked into `agents/<vendor>/` for each tool family (claude, cursor, codex).

## Canonical layout

```
.ai/
├── skills/              ← canonical skills (`SKILL.md` + optional refs/scripts/assets)
├── agents/              ← canonical subagents (single `.md` files)
├── rules/               ← cross-vendor rules (`*.mdc` with frontmatter)
├── prompts/             ← reusable audit/review prompts
└── artifacts/           ← gitignored ephemeral working files

agents/
├── claude/              ← Claude Code vendor dir (skills/ and agents/ are symlinks into ../../.ai/)
├── cursor/              ← Cursor vendor dir
├── codex/               ← Codex vendor dir
└── shared/              ← cross-vendor scripts (validate-skills.sh, mcp-servers.json, …)

docs/
├── specs/               ← phased plans (this kind of doc)
├── adr/                 ← architecture decision records
└── skills-sources.md    ← upstream attribution registry
```

## Flagged ambiguities

- "agent" was used to mean both **subagent** (the dispatched worker) and **the AI as a whole**. In this repo, **agent** specifically means a subagent file in `.ai/agents/` or `agents/<vendor>/agents/`.
- "plugin" was overloaded with general extension language. In this repo, **plugin** is specifically a Claude Code plugin manifest entry.
