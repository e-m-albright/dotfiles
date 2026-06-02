# Skill Sources Registry

Single source of truth for upstream attribution. Maps each ported / adapted skill in this repo to its inspiration, pinned to the commit SHA we last reviewed.

When upstream evolves, refresh `last_reviewed_commit` for the repo and re-diff against our copy to harvest refinements. See `.ai/skills/skill-creator/references/skill-format.md` for the full attribution convention.

## Per-skill attribution

| Skill | Upstream | Pinned commit | Ported | Adaptations |
|-------|----------|---------------|--------|-------------|
| `diagnose` | [mattpocock/skills/engineering/diagnose](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/diagnose/SKILL.md) | `733d312` | 2026-05-07 | Verbatim port. Cross-references to `/improve-codebase-architecture` and project glossary/ADRs preserved (resolve when those land). |
| `grill-with-docs` | [mattpocock/skills/engineering/grill-with-docs](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/grill-with-docs/SKILL.md) | `733d312` | 2026-05-07 | Refs (`CONTEXT-FORMAT.md`, `ADR-FORMAT.md`) moved into `references/` per Anthropic spec. Description gained literal-phrase triggers. |
| `tdd-vertical-slices` | [mattpocock/skills/engineering/tdd](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/tdd/SKILL.md) | `733d312` | 2026-05-07 | Renamed from `tdd` to avoid namespace collision with `superpowers:test-driven-development`. 5 ref files moved into `references/`. Description rewritten with literal-phrase triggers and explicit complementarity note. |
| `improve-codebase-architecture` | [mattpocock/skills/engineering/improve-codebase-architecture](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/improve-codebase-architecture/SKILL.md) | `733d312` | 2026-05-07 | 3 ref files (`LANGUAGE.md`, `DEEPENING.md`, `INTERFACE-DESIGN.md`) moved into `references/`. Cross-skill links to `grill-with-docs` updated for new `references/` subpath. Description gained literal-phrase triggers. |
| `prototype` | [mattpocock/skills/engineering/prototype](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/prototype/SKILL.md) | `733d312` | 2026-05-07 | Refs (`LOGIC.md`, `UI.md`) moved into `references/`. Description gained literal-phrase triggers. |
| `code-quality-audit` (criterion U11) | [mattpocock/skills/engineering/improve-codebase-architecture/LANGUAGE.md](https://github.com/mattpocock/skills/blob/733d312/skills/engineering/improve-codebase-architecture/LANGUAGE.md) | `733d312` | 2026-05-07 | Extracted "deletion test" + module depth principle as new universal criterion U11 in our existing `code-quality-audit` skill. |
| `skill-creator` | [anthropics/skills/skill-creator](https://github.com/anthropics/skills/blob/d211d43/skills/skill-creator/SKILL.md) | `d211d43` | 2026-05-07 | Streamlined from 485 to ~230 lines. Stripped Anthropic's eval-runner infrastructure (run_loop.py, aggregate_benchmark.py, eval-viewer/, blind-comparison agents, packaging) and Claude.ai/Cowork sections. `references/schemas.md` ported verbatim. Pointed at our `validate-skills.sh` and `skill-format.mdc`. |

## Per-agent attribution

Subagents in `.ai/agents/` (canonical, symlinked into `agents/{claude,cursor,codex}/agents/`).

| Agent | Upstream | Pinned commit | Ported | Adaptations |
|-------|----------|---------------|--------|-------------|
| `security-auditor` | [wshobson/agents/.../security-auditor.md](https://github.com/wshobson/agents/blob/ece811f/plugins/backend-development/agents/security-auditor.md) | `ece811f` | 2026-05-07 | Added `tools: Read, Grep, Glob, Bash` + body-level read-only constraint. Description rewritten with literal triggers; `PROACTIVELY` dropped. |
| `performance-engineer` | [wshobson/agents/.../performance-engineer.md](https://github.com/wshobson/agents/blob/ece811f/plugins/backend-development/agents/performance-engineer.md) | `ece811f` | 2026-05-07 | Added `tools` restriction + body-level read-only constraint. Description rewritten. |
| `debugger` | [wshobson/agents/.../debugger.md](https://github.com/wshobson/agents/blob/ece811f/plugins/incident-response/agents/debugger.md) | `ece811f` | 2026-05-07 | Description rewritten with complementarity note vs `diagnose` skill. Body gained explicit `Output Format` section. |
| `error-detective` | [wshobson/agents/.../error-detective.md](https://github.com/wshobson/agents/blob/ece811f/plugins/incident-response/agents/error-detective.md) | `ece811f` | 2026-05-07 | Added `tools` restriction + body-level read-only constraint. Body gained explicit `Output Format`. |
| `legacy-modernizer` | [wshobson/agents/.../legacy-modernizer.md](https://github.com/wshobson/agents/blob/ece811f/plugins/code-refactoring/agents/legacy-modernizer.md) | `ece811f` | 2026-05-07 | Description rewritten; `PROACTIVELY` dropped. Body gained explicit `Purpose` and `Output Format` sections. |

(Existing `shellcheck-reviewer.md` is original to this repo; triplicated as real files in each vendor — separate cleanup.)

## Reference repos (last reviewed 2026-05-07)

| Repo | Last reviewed commit | Reviewed on | License | Why we care |
|------|---------------------|-------------|---------|-------------|
| [mattpocock/skills](https://github.com/mattpocock/skills) | [`733d312`](https://github.com/mattpocock/skills/commit/733d312884b3878a9a9cff693c5886943753a741) | 2026-05-07 | MIT | Process skills (diagnose, grill-with-docs, tdd, improve-codebase-architecture, prototype). Best-in-class engineering process library — Phase 2 borrows. |
| [anthropics/skills](https://github.com/anthropics/skills) | [`d211d43`](https://github.com/anthropics/skills/commit/d211d437443a7b2496a3dad9575e7dddd724c585) | 2026-05-06 | Apache-2.0 (examples) / proprietary source-available (docx, pdf, pptx, xlsx) | Canonical skill spec authority + `skill-creator` meta-skill + `evals.json` schema. Phase 5 borrows for distribution and meta. |
| [wshobson/agents](https://github.com/wshobson/agents) | [`ece811f`](https://github.com/wshobson/agents/commit/ece811f23310a37ceb43496dbac0e244fe6845b6) | 2026-05-02 | MIT | 80-plugin marketplace. Terse agent template, `security-auditor` / `debugger` / `error-detective`, `conductor` spec-driven workflow, `plugin-eval` framework. Phase 3 + Phase 4 borrows. |

## Process

**When porting a skill from upstream:**
1. Read the upstream SKILL.md at the registry's pinned commit (or a newer one if we're re-reviewing — bump the row first).
2. Adapt: remove upstream-specific references, replace links, adjust voice to our conventions.
3. Add frontmatter `metadata.source_url`, `source_commit`, `ported_at`, `adaptations`.
4. Add `## Sources` footer at end of SKILL.md body linking the upstream pinned commit.
5. Add a row to the per-skill table above.

**When updating an already-ported skill:**
1. Compare current upstream against our pinned commit.
2. Edit our SKILL.md as needed.
3. Bump `source_commit` and `ported_at` in frontmatter; append the change summary to `adaptations`.
4. Update the row in the per-skill table.

**When re-reviewing an upstream repo (no specific port in mind):**
1. Update the "Reference repos" row's `last_reviewed_commit` and `Reviewed on`.
2. Note in a local spec scratch file (under `docs/specs/`, gitignored) anything new worth porting.

## Future: regenerate from frontmatter

The per-skill table above is manually maintained for now. Future improvement: a `bin/dotfiles list-skill-sources` subcommand walks `.ai/skills/*/SKILL.md`, extracts frontmatter `metadata.source_*` fields, and regenerates this table. Tracked as a follow-up in the research spec doc.
