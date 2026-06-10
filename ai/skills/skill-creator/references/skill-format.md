# Skill Format

Conventions for authoring and maintaining skills in `ai/skills/`. Aligns with [Anthropic's official skill spec](https://agentskills.io/specification) with project-specific additions for source attribution and tool restrictions.

## Frontmatter

**Required:**
- `name` — must equal parent directory name. `[a-z0-9-]` only. No leading/trailing/consecutive hyphens. Max 64 chars.
- `description` — what the skill does + when to use it. Max 1024 chars. Always include a `Use when …` clause with literal user phrases (see below).

**Optional (Anthropic spec):**
- `license` — license name or reference to a bundled `LICENSE.txt`.
- `compatibility` — environment requirements. Max 500 chars.
- `metadata` — arbitrary string→string map. Custom fields go here, never at top level.
- `allowed-tools` — space-separated pre-approved tools (experimental, see §Tool restrictions).
- `disable-model-invocation: true` — skill never auto-triggers; only invoked when the user explicitly types `/<name>`.
- `argument-hint` — for skills that take arguments (`argument-hint: "What's the project path?"`).

**Our additions (always under `metadata:`):**
- `source_url` — upstream URL when the skill is ported/adapted.
- `source_commit` — pinned commit SHA at time of porting.
- `ported_at` — ISO date.
- `adaptations` — short note describing what changed from upstream.

## Description format

Two-clause: `<what it does>. Use when <triggers>.`

Triggers should be concrete, comma-separated:
- Literal phrases users say (`"open a PR"`, `"is my env healthy?"`, `"audit this"`).
- File markers (`mentions a .pdf`, `imports anthropic SDK`).
- Concrete scenarios (`after running install`, `before merging`, `during incident`).

For skills at risk of false-firing on adjacent topics, add explicit `SKIP:` or `Do NOT trigger when …` clauses (Anthropic's `claude-api` description is the canonical example).

`disable-model-invocation: true` skills should still include the `Use when` clause — it disambiguates explicit invocation, even if it doesn't drive auto-triggering.

## Body conventions

- **Imperative voice.** "Run X." not "The user can run X."
- **Avoid `ALWAYS` / `NEVER` in caps.** Explain *why* a rule exists. Anthropic flag: "rigid all-caps rules are a yellow flag for a brittle skill."
- **Numbered phases / checklists** at end of phases for repeatable processes.
- **≤ 500 lines per Anthropic spec.** If exceeding, split into `references/` and link with one-level-deep paths.

## Sub-folders (Anthropic-canonical only)

- `scripts/` — executable code, called as black-box. Always include this paragraph in SKILL.md when bundling scripts:
  > *DO NOT read the source until you try running the script first and find that a customized solution is absolutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.*
- `references/` — on-demand docs linked from SKILL.md as `[label](references/foo.md)`.
- `assets/` — output templates (HTML scaffolds, fonts, etc.).

Avoid ad-hoc folder names. `examples/` and `templates/` are tolerated where idiomatic.

## Tool restrictions (`allowed-tools`)

Use for read-only audit/review skills that should never edit files. Format is space-separated:

```yaml
allowed-tools: Read Grep Glob Bash(git:*) Bash(wc:*)
```

Marked **experimental** in the Anthropic spec. Test that it works in the target harness before relying on it for security boundaries. If unsure, also document the read-only contract in the body so reviewers can audit it.

## Source attribution

Skills ported or substantially adapted from upstream MUST include attribution:

1. **Frontmatter** under `metadata`:
   ```yaml
   metadata:
     source_url: https://github.com/mattpocock/skills/blob/main/skills/engineering/systematic-debugging/SKILL.md
     source_commit: 733d312884b3878a9a9cff693c5886943753a741
     ported_at: 2026-05-07
     adaptations: Removed CLAUDE.md-specific references; tightened phase 4 example.
   ```

2. **Body footer** at end of SKILL.md:
   ```markdown
   ## Sources
   - Adapted from [mattpocock/skills/engineering/systematic-debugging](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/systematic-debugging/SKILL.md) (ported 2026-05-07).
   ```

3. **Central registry** at `docs/skills-sources.md` — single source of truth for cross-skill review. Add a row when porting; refresh when re-reviewing upstream.

## Why source attribution matters

Upstream skills evolve. Pinning a commit SHA lets us:
- Diff our copy against later upstream commits to harvest refinements.
- Trace inspiration back to the original author.
- Decide whether to re-port wholesale or merge specific changes.

When updating an already-ported skill: bump `source_commit` + `ported_at`, append to `adaptations`, update the registry row.

## Lifecycle (deferred to Phase 5)

When we adopt Matt Pocock's bucketing pattern, skills will move under:
- `ai/skills/engineering/<name>/` — daily code work
- `ai/skills/productivity/<name>/` — workflow, non-code
- `ai/skills/misc/<name>/` — rare utilities
- `ai/skills/personal/<name>/` — never in plugin manifest
- `ai/skills/in-progress/<name>/` — drafts, never in plugin manifest
- `ai/skills/deprecated/<name>/` — retired, never in plugin manifest

Currently flat under `ai/skills/`. Migration deferred until enough skills exist for the structure to earn its cost. See historical skills-research notes (Phase 5; was under `docs/specs/`, now scrubbed).

_Promoted from `.ai/rules/process/skill-format.mdc` into this skill's references._
