# Agent Format

Conventions for authoring subagents in `.ai/agents/` (canonical) and `agents/<vendor>/agents/` (vendor symlinks). Subagents are dispatched via the `Agent` tool; they have isolated context and a focused task scope.

## Frontmatter

**Required:**
- `name` — must equal filename (without `.md`). `[a-z0-9-]` only.
- `description` — what the agent does + when to use it. Includes literal `Use when …` trigger clause per the same convention as skills (see `skill-format.mdc`).

**Optional:**
- `tools` — **comma-separated** list (different from skills' space-separated `allowed-tools`). Restricts what the subagent can call. Use for read-only review/audit agents.
- `model` — `opus`, `sonnet`, `haiku`, or `inherit`. Default to `sonnet` for most agents; `opus` for high-stakes review or architecture work; `haiku` for narrow deterministic tasks.
- `color` — UI color in some hosts (cyan, blue, etc.). Optional, mostly aesthetic.

**Source attribution (under any custom block — agents don't have a spec'd `metadata` field):** put attribution in a `## Sources` footer at end of body and a row in `docs/skills-sources.md`. Do NOT invent a custom top-level frontmatter field — it can break harnesses that strict-parse YAML.

## Description format

Same convention as skills: `<what the agent does>. Use when <triggers>.`

**Drop `PROACTIVELY` unless you really want auto-invocation.** wshobson's collection uses `PROACTIVELY` on ~60% of agents, which makes them too eager. Reserve it for agents that should genuinely auto-fire (e.g. a code-reviewer running on every PR-shaped diff). Most audit/specialist agents should be deliberately summoned.

## Body — terse template (canonical)

Cap the body at ~3 KB. Sections in this order:

```markdown
You are a <one-sentence role definition>.

## Purpose

<2-3 sentences naming the goal and the boundaries.>

## Capabilities

- **<Capability area>**: <what's in scope, comma-separated specifics>
- **<Capability area>**: <...>
- ...

## Response Approach

1. <Numbered, observable step>
2. <...>
5. <Final synthesis step>

## Output Format

<Specific structure the agent should produce. Severity tiers, file:line references, "End with a summary…" — concrete shape, not vague guidance.>
```

Avoid "encyclopedic capability lists" — wshobson's worst agents (8–10 KB bodies) read like brochure copy. Aim for the 1.5-3 KB band.

## Tool restrictions

For read-only review/audit agents, restrict tools:

```yaml
tools: Read, Grep, Glob, Bash
```

`Bash` here is unrestricted — Claude Code's agent format doesn't support `Bash(pattern:*)` subcommand restriction the way skills' `allowed-tools` does. Compensate by adding a body-level constraint:

> "You MUST NOT modify any files. Use Bash only for read-only operations (`git log`, `git diff`, `rg`, `find`, `wc`)."

For agents that legitimately edit files (refactoring, code generation), omit `tools` to keep full access — but add the body-level scope so the agent knows what it's allowed to touch.

## Sources block

If the agent is ported / adapted from upstream, add at end of body:

```markdown
## Sources
- Adapted from [wshobson/agents/.../agent-name.md](URL_at_pinned_commit) (ported YYYY-MM-DD, MIT). <One-line summary of changes.>
```

And add a row to `docs/skills-sources.md` (Agents section).

## Canonical + symlink layout

New agents follow the same convention as skills:

- Canonical file: `.ai/agents/<name>.md`
- Vendor symlinks: `agents/{claude,cursor,codex}/agents/<name>.md` → `../../../.ai/agents/<name>.md`

Editing the canonical updates all vendors. (Legacy: `shellcheck-reviewer.md` is still triplicated as real files — separate cleanup.)

_Promoted from `.ai/rules/process/agent-format.mdc` into this skill's references._
