# Repository Context

Glossary for the agentic-tooling vocabulary used in this dotfiles repo. Several concepts look alike from a distance — disambiguating them up front saves churn. The big one: **"agent"** means three different things here (a coding tool, a dispatched worker, and a CLI namespace); see [Flagged ambiguities](#flagged-ambiguities).

## Language

**Agent** (coding tool / vendor):
One of the AI coding tools we deploy configuration to — Claude Code, Cursor, Codex, Gemini, Pi. Each has a directory under `ai/agents/<name>/`. In the CLI this is the `Agent` type (an enum of those five). The `dotfiles agent` command namespace operates on them: `dotfiles agent setup` deploys config to every agent; `dotfiles agent lint` validates skills/subagents; `dotfiles agent overview` shows what each one has.
_Avoid_: "vendor" (the old code name — renamed to `Agent`), "provider".

**Subagent**:
A worker dispatched via the `Agent` tool with isolated context and a focused task. Canonical source is a single file at `ai/subagents/<name>.md`. Deployed by a small `cp` loop into each agent's worker dir (`~/.claude/agents/`, `~/.codex/agents/`, `~/.pi/agent/agents/`). Different frontmatter from skills (`tools` is comma-separated; no `allowed-tools`). See `ai/skills/skill-creator/references/agent-format.md`.
_Avoid_: assistant, helper, model. **Not** the same as an *Agent* (coding tool) above.

**Skill**:
A capability triggered by description match, loaded progressively. Canonical source lives at `ai/skills/<name>/SKILL.md` (+ optional `references/`, `scripts/`, `assets/`). Deployed to each agent's user-level skills dir via the public `npx skills` CLI (`~/.claude/skills/`, `~/.agents/skills/` for Codex/Pi) — real files are copied, **not** symlinked, and there are no per-agent mirror dirs in this repo. Its frontmatter `description` is the only trigger surface — see `ai/skills/skill-creator/references/skill-format.md`.
_Avoid_: command, prompt.

**Rule**:
Persistent ambient guidance loaded into every session. There is exactly **one** hand-authored kernel — `ai/agents/shared/rules.md` — deployed verbatim to every agent by `dotfiles agent setup` (Cursor gets a generated YAML-frontmatter wrapper, `rules/shared-rules.mdc`; others get it inlined into their instructions file). No per-rule `.mdc` files, no glob-based loading, no baking. Language- and framework-specific taste is **not** a rule — it lives as reference in `docs/stacks/`.
_Avoid_: convention, policy (fine in prose, but the artifact is "the kernel" / "rules.md").

**Hook**:
A shell command the harness runs in response to a tool-use event (`PreToolUse`, `PostToolUse`, `Stop`, `Notification`). Configured in `ai/agents/<vendor>/hooks.json`. Runs outside the model's awareness — exit code 2 blocks the action.
_Avoid_: trigger, listener.

**MCP server**:
An external process exposing tools/resources/prompts via the Model Context Protocol. Shared servers are declared in `ai/agents/shared/mcp-servers.json` and merged into each agent's config. Loaded per session; consumes context window.
_Avoid_: tool provider, plugin (those mean other things here).

**Plugin**:
A Claude Code plugin we **enable** from an external marketplace — listed in `ai/agents/claude/plugins.yaml` and merged into `~/.claude/settings.json` (`enabledPlugins`), with its marketplace registered via `ai/agents/claude/marketplaces.json` (`extraKnownMarketplaces`). This repo no longer publishes its own marketplace manifest. Evaluation notes (tried / removed / disabled) live in `ai/agents/plugin-notes.md`.
_Avoid_: package, extension.

**Slash command**:
A skill or workflow invocable via `/<name>` in the harness. We don't ship custom slash commands today — they're conceptually subsumed by skills.

## Relationships

- An **Agent** (coding tool) receives config from `dotfiles agent setup`: the rule kernel, skills, subagents, hooks, MCP servers, and a statusline.
- A **skill** is described by its frontmatter and triggers on user phrases / contexts; a **subagent** is dispatched by another agent with a focused task.
- The **rule kernel** loads ambient guidance; **hooks** intercept tool calls; **MCP servers** add new tools; **plugins** bundle skills/commands from a marketplace.
- Canonical AI assets live **once** under `ai/` and are *deployed* (copied / generated) into each agent's user-level directories at setup time — there are no per-agent mirror dirs or symlink farms tracked in this repo.

## Canonical layout

```
ai/
├── agents/              ← per-agent deploy config, one dir each:
│   ├── claude/          ←   plugins.yaml, marketplaces.json, hooks/, permissions.json, statusline.sh
│   ├── cursor/          ←   rules/ (generated shared-rules.mdc), hooks/, cli-config.json, plugin
│   ├── codex/           ←   default.rules, hooks.json, statusline.toml
│   ├── gemini/          ←   settings.json source
│   ├── pi/              ←   settings/models (JSONC), extensions/
│   └── shared/          ←   rules.md (THE kernel), mcp-servers.json, ignore-patterns
├── skills/              ← canonical skills (`SKILL.md` + optional refs/scripts/assets)
├── subagents/           ← canonical subagents (single `.md` files)
├── prompts/             ← system-prompt artifacts (advisor/detailed, gemini-chunks/)
├── audits/              ← cadence bot-audit prompts (run by schedules; also ad hoc)
└── artifacts/           ← gitignored ephemeral working files

docs/
├── adr/                 ← architecture decision records (numbered, committed)
├── stacks/              ← per-language taste (pick/avoid, idioms) — NOT pushed as rules
├── knowledge/           ← cross-cutting practice (ai-tools, prompting/, token-efficiency, …)
├── specs/               ← phased plans (gitignored)
└── skills-sources.md    ← upstream skill attribution registry
```

Deployment is one-directional: edit the canonical source under `ai/`, run `dotfiles agent setup`, and it lands in `~/.claude`, `~/.cursor`, `~/.codex`, `~/.gemini`, `~/.pi/agent`, and the shared `~/.agents/skills`.

## Flagged ambiguities

- **"agent" is three things.** (1) A *coding tool* we configure — a dir under `ai/agents/` and the `Agent` type in code. (2) A *subagent* — a dispatched worker file under `ai/subagents/`. (3) The `dotfiles agent` *CLI namespace*. When unqualified, "agent" usually means the coding tool; say "subagent" for the dispatched worker.
- **"plugin"** is specifically a Claude Code plugin enabled from a marketplace — not general extension/package language, and not an MCP server.
- **"rule"** is the single shared kernel, not a per-language convention file (those are `docs/stacks/` reference, deliberately *not* deployed as rules).
