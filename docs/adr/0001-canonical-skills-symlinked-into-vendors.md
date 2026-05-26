# Canonical skills and agents live in `.ai/`, vendor dirs symlink into them

**Date**: 2026-04-29 (in effect since the backport phase 3); ratified as ADR 2026-05-07.
**Status**: **superseded by [ADR-0002](0002-canonical-skills-deploy-via-npx-skills.md) on 2026-05-07** — the per-skill symlink approach was abandoned in favor of `npx skills` deploy directly from `.ai/skills/`. Per-vendor mirror dirs were deleted entirely.

## Context

We support three agentic tools (Claude Code, Cursor, Codex). Each expects a vendor-specific directory:
- `agents/claude/skills/` and `agents/claude/agents/`
- `agents/cursor/skills/` and `agents/cursor/agents/`
- `agents/codex/skills/` and `agents/codex/agents/`

Naively, this means triplicate copies of every skill and agent — leading to drift the moment any one copy is edited.

## Decision

Canonical skill source: **`.ai/skills/<name>/SKILL.md`** (with optional `references/`, `scripts/`, `assets/`).
Canonical agent source: **`.ai/agents/<name>.md`**.

Each `agents/<vendor>/skills/<name>` is a **symlink** to `../../../.ai/skills/<name>`.
Each `agents/<vendor>/agents/<name>.md` is a **symlink** to `../../../.ai/agents/<name>.md`.

Vendor-only artifacts (rare) stay as real files inside their vendor dir — e.g. `agents/claude/skills/agents-overview/`.

## Why

- **Single source of truth.** Edit once, all three vendors update.
- **No drift.** Symlinks resolve at read time; vendor dirs always reflect the canonical content.
- **Setup-script transparency.** `setup.sh` walks `agents/<vendor>/skills/*/SKILL.md`; symlinks resolve transparently. No special case needed.
- **Source attribution travels with the canonical file.** `metadata.source_*` in frontmatter is one place, not three.

## Trade-offs

- Symlinks don't survive every deployment context. `git` handles them; `tar` mostly handles them; some Windows tooling does not. We assume macOS/Linux only.
- `bin/dotfiles validate-skills` walks the canonical `.ai/skills/` and `.ai/agents/` to avoid double-counting. The legacy `shellcheck-reviewer.md` was triplicated as real files until 2026-05-07 when it was canonicalized to match this pattern.
- A new `.ai/skills/<name>/` requires a manual `ln -s` into each vendor dir. We tolerate this for now; a `bin/dotfiles link-skills` subcommand could automate it (deferred — current pace is low).

## See also

- `CONTEXT.md` — vocabulary including the canonical-+-symlink layout.
- `.ai/rules/process/skill-format.mdc` — author-side conventions.
- `.ai/rules/process/agent-format.mdc` — same for agents.
- `docs/specs/2026-05-07-skills-research.md` (local notes) — Phase 2 + 3 + 4 of the cross-repo skills research, where this pattern was extended to agents.
