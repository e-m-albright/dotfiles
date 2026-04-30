# Ophira → Dotfiles Backport

**Date**: 2026-04-28
**Status**: Phases 1, 2, and 3 shipped.

Ophira (`~/code/private/ophira`) has matured an agentic-programming foundation that's measurably better than dotfiles' current scaffolding. This spec captures what to bring back, in what order, and what to leave behind.

## What Ophira does that dotfiles doesn't

| Pattern | Where it lives in Ophira | Status in dotfiles |
|---------|--------------------------|--------------------|
| Code health ratchet (`baselines.json`, monotonic ceilings) | `baselines.json` + `scripts/check_baselines.py` + `lefthook.yml` | Missing |
| Two-phase audit pipeline (tools-first, LLM-synth) | `just/audit/`, `scripts/audit/`, `.ai/artifacts/audits/` | Missing |
| Reusable audit prompt library (~20 prompts) | `.ai/prompts/audits/`, `.ai/prompts/review/` | Missing |
| Artifact placement zones (durable / in-flight / ephemeral) | `.ai/rules/artifact-placement.mdc` + gitignored `.ai/artifacts/` | Partial — has `.ai/rules/process/agent-artifacts.mdc` but no zone discipline |
| Engineering philosophy as single source | `docs/engineering/code-health-manifesto.md` (20 principles) + `design-principles.md` (55 + 25-question audit) | Missing — scattered across rule files |
| Graded code-quality audit skill | `.ai/skills/code-quality-audit/SKILL.md` (rubric A–F across U1–U10 + surface criteria) | Missing |
| Frontmatter convention + validator | YAML frontmatter on every `.ai/**/*.md`; validated by `scripts/audit/ai_usage.py` | Frontmatter inconsistent; no validator |
| Cross-tool symlink strategy for `.ai/` | `.cursor/rules/*.mdc` → `.ai/rules/*.mdc`; `.claude/{rules,skills}` → `.ai/{rules,skills}` | Dotfiles symlinks `process/*.mdc` to user-level only |
| Recurring audit schedule | Claude Code scheduled triggers (2/day × 7-day cycle) | Not used |

## Phases

### Phase 1 — universal patterns (this turn)

Additive, low-risk changes that ingest the most-portable parts of the Ophira system without restructuring scaffold output.

- [x] `.ai/artifacts/` zone (gitignored) — ephemeral working files
- [x] `.ai/prompts/audits/` directory with universal audit prompts (god-functions, abstractions, coupling, duplication)
- [x] `.ai/skills/code-quality-audit/SKILL.md` — language-agnostic graded rubric
- [x] `.ai/rules/process/artifact-placement.mdc` — universal version, no Ophira-specific paths
- [x] `docs/engineering-philosophy.md` — 12 universal principles distilled from Ophira's manifesto
- [x] AGENTS.md / README.md updates pointing at new structure

### Phase 2 — scaffold integration (DONE)

Made `prompts/scaffold.sh` opt-in deploy the audit pipeline + baselines.

- [x] `prompts/scaffolds/audit-pipeline/` — portable `security.sh`, `ai_usage.py`, `just/audit/mod.just`, plus `.ai/prompts/audits/` (security, ai-usage, plus the 4 universal structural prompts mirrored from Phase 1)
- [x] `prompts/scaffolds/baselines/` — `baselines.json` template, project-portable `check_baselines.py` (rg-first, grep fallback, METRICS table), `lefthook.baselines.yml` fragment
- [x] `scaffold.sh` flags: `--with-audit-pipeline`, `--with-baselines`, `--with-code-health` (both)
- [x] Frontmatter validator (`ai_usage.py`) — runs on dotfiles itself; caught my Phase 1 audit prompts missing frontmatter (now fixed)
- [ ] Deferred: `prompts/scaffolds/ai-folder/` template — current `scaffold.sh` already creates the right `.ai/` shape; left as TODO if/when we add the universal audit prompts to every new project automatically

### Phase 3 — dotfiles' own enforcement (DONE)

Applied the patterns to dotfiles itself.

- [x] `baselines.json` at repo root — `todo_total: 0`, `hardcoded_user_path: 0`, file ceilings on the 7 largest scripts (auto-ratcheted to current values: scaffold.sh=1056, claude/setup.sh=568, test_scaffold.sh=480, brew.sh=408, install.sh=360, codex/setup.sh=223, cursor/setup.sh=217)
- [x] `scripts/check_baselines.py` — dotfiles-specific METRICS (bash-flavoured, excludes scaffold templates and worktree mirrors so generated TODO strings don't trip the ratchet)
- [x] `lefthook.yml` — added `baselines` pre-commit step alongside existing shellcheck/yaml-lint/json-lint
- [x] Cross-tool skill refactor — `.ai/skills/` is now canonical; the 9 universal skills moved there once. Each `agents/{claude,cursor,codex}/skills/<universal>` is a symlink to `../../../.ai/skills/<universal>`. Vendor-only skills (claude's `agents-overview`) stay as real dirs. Setup scripts unchanged — they walk `agents/<vendor>/skills/*/SKILL.md` and the symlinks resolve transparently. Eliminated ~24 duplicate SKILL.md copies.
- [ ] Deferred: periodic code-health audit on dotfiles via the `agents-overview` skill — needs the extension hook design first.

## What we're not bringing over

- Healthcare domain vocabulary, Ophira-specific service names, healthcare compliance rules
- The 55-principle design doc (too heavy for a starter scaffold; 12 universals cover the load-bearing rationale)
- Project-specific audit prompts (`prompt-regression`, `cost-and-token-burn`, `migration-debt`)
- Ophira's specific tech-stack rules (Axum, PydanticAI, SvelteKit-specific patterns) — those already exist in dotfiles' `.ai/rules/frameworks/`
- Ophira's recurring trigger schedule — needs per-project tuning, not a universal default

## Resolved questions

- **Symlink vs. copy for `.ai/skills/`**: Resolved — symlinks. Phase 3 promoted 9 universal skills into `.ai/skills/` and replaced the per-vendor copies with directory symlinks. Setup scripts didn't need to change (the glob `agents/<vendor>/skills/*/SKILL.md` resolves transparently through dir symlinks).
- **Should `code-quality-audit` skill ship with dotfiles or only be scaffolded into projects?** Resolved — both. It lives in `.ai/skills/` (deployed to every Claude Code/Cursor/Codex session via setup scripts) and the audit-pipeline scaffold ships its own copy of the audit prompts so projects get a self-contained version.
- **Frontmatter validator**: Resolved in Phase 2 — `prompts/scaffolds/audit-pipeline/scripts/audit/ai_usage.py` runs cleanly on dotfiles itself; caught and fixed missing frontmatter on the 4 universal audit prompts.
