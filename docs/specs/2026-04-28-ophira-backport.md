# Ophira → Dotfiles Backport

**Date**: 2026-04-28
**Status**: Phase 1 in progress; Phases 2–3 deferred for review.

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

### Phase 2 — scaffold integration (next session)

Make `prompts/scaffold.sh` produce projects with this structure baked in.

- [ ] `prompts/scaffolds/ai-folder/` template (artifacts/, prompts/, skills/, rules/)
- [ ] `prompts/scaffolds/audit-pipeline/` — `scripts/audit/security.sh`, `scripts/audit/ai_usage.py`, `just/audit/mod.just` stubs
- [ ] `prompts/scaffolds/baselines/` — `baselines.json` template + checker stub + lefthook integration
- [ ] `scaffold.sh` flag: `--with-audit-pipeline` to opt into the heavier setup
- [ ] Frontmatter validator: `scripts/audit/ai_usage.py` adapted to be project-portable

### Phase 3 — dotfiles' own enforcement (deferred)

Apply the patterns to dotfiles itself.

- [ ] `dotfiles/baselines.json` — initial counts (small repo, mostly bash)
- [ ] `lefthook.yml` ratchet hooks
- [ ] Periodic code-health audit on dotfiles via `dotfiles agents-overview` extension
- [ ] Cross-tool symlink refactor — `.ai/skills/` → `~/.claude/skills/`, `~/.cursor/skills/` (Phase 2 prerequisite)

## What we're not bringing over

- Healthcare domain vocabulary, Ophira-specific service names, healthcare compliance rules
- The 55-principle design doc (too heavy for a starter scaffold; 12 universals cover the load-bearing rationale)
- Project-specific audit prompts (`prompt-regression`, `cost-and-token-burn`, `migration-debt`)
- Ophira's specific tech-stack rules (Axum, PydanticAI, SvelteKit-specific patterns) — those already exist in dotfiles' `.ai/rules/frameworks/`
- Ophira's recurring trigger schedule — needs per-project tuning, not a universal default

## Open questions

- **Symlink vs. copy for `.ai/skills/`**: Ophira symlinks. Dotfiles currently mirrors files between `agents/claude/skills/` and `agents/cursor/skills/` (manually duplicated). Symlinks would deduplicate at the cost of harder-to-edit state. Defer to Phase 2.
- **Should `code-quality-audit` skill ship with dotfiles or only be scaffolded into projects?** Phase 1 puts it in `.ai/skills/` so any Claude Code session in any directory can invoke it. Phase 2 may also stamp it into new projects.
- **Frontmatter validator**: Worth porting now or wait for the audit pipeline scaffold? Deferred to Phase 2 since dotfiles has only a handful of `.mdc` files.
