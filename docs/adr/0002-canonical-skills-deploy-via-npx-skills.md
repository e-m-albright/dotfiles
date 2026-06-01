# Canonical skills deploy via `npx skills`; per-vendor mirror dirs are deleted

**Date**: 2026-05-07.
**Status**: accepted.
**Supersedes**: [ADR-0001](0001-canonical-skills-symlinked-into-vendors.md).

## Context

ADR-0001 established a canonical-+-symlink pattern: skills lived in `.ai/skills/<name>/`, with per-vendor mirror dirs `agents/{claude,cursor,codex}/skills/<name>` as symlinks pointing to the canonical. Same for `.ai/agents/` → `agents/<vendor>/agents/<name>.md`.

Three problems surfaced:

1. **Per-skill symlinks were tedious.** Adding a new skill required N `ln -s` commands across vendors. Bucketing was being considered as a way to scale this — but bucketing is orthogonal to the sync mechanism.
2. **Our `setup.sh` only copied `SKILL.md`, not bundled refs/scripts/assets.** Discovered while porting Matt Pocock's skills: `diagnose/scripts/`, `grill-with-docs/references/`, `tdd-vertical-slices/references/` etc. never reached the install destination. Real bug.
3. **Symlinks at the install destination (`~/.claude/skills/`) are buggy in Claude Code** ([anthropics/claude-code#14836](https://github.com/anthropics/claude-code/issues/14836), [#25367](https://github.com/anthropics/claude-code/issues/25367), [#50052](https://github.com/anthropics/claude-code/issues/50052)). Auto-updates have been observed deleting symlinks under `~/.claude/skills/`. Even if our setup-script copies real files, future patches could regress.

Meanwhile, the public ecosystem converged on a copy-based CLI: **[`vercel-labs/skills`](https://github.com/vercel-labs/skills) (`npx skills`)** — 17k stars, the de-facto distribution tool. It accepts a local path as a source, walks `<path>/<skill>/SKILL.md`, and deploys to each vendor's user-level dir as real files (`--copy`). Supports 50+ vendors including Claude Code, Codex, Cursor, etc.

## Decision

**Skills deploy via `npx skills`. Per-vendor mirror dirs are deleted.**

- **Canonical**: `.ai/skills/<name>/SKILL.md` (with optional `references/`, `scripts/`, `assets/`).
- **Deploy**: each vendor's `setup.sh` runs:
  ```bash
  npx skills add "$DOTFILES_DIR/.ai/skills" -s '*' -a <vendor> -g -y --copy
  ```
- **No more `agents/<vendor>/skills/`**. Deleted.
- **Subagents** (`.ai/agents/<name>.md`, single-file format) deploy via a small `cp` loop in each vendor's `setup.sh` — `npx skills` only handles SKILL.md-shaped skills.
- **No more `agents/<vendor>/agents/`**. Deleted.
- **`agents-overview` skill** (formerly Claude-only at `agents/claude/skills/agents-overview/`) moved to `.ai/skills/agents-overview/`. Now cross-vendor — its content already references both Claude Code and Cursor.

## Why

- **One canonical, one deploy command.** Adding a skill = create directory in `.ai/skills/`. Run `dotfiles agent-setup`. Done.
- **Public tool does the heavy lifting.** `npx skills` knows each vendor's true install path, supports `--copy` to sidestep the Claude Code symlink bug, and is what 17k+ users already use to install third-party skills (we already used it for `external-skills.txt`).
- **Whole-directory copy by default.** `--copy` deploys SKILL.md plus `references/`, `scripts/` (executable bit preserved), and `assets/` correctly. Fixes the bug from ADR-0001 era.
- **No drift, no mirror dirs to keep in sync.** Editing `.ai/skills/diagnose/SKILL.md` is the only place to edit.
- **Cursor falls out gracefully.** Cursor doesn't have a skills concept; `npx skills` doesn't list it as a target. We deploy nothing skills-related to Cursor — just rules and MCP, as before.

## Trade-offs

- **Hard dependency on `npx`** (i.e. Node.js). Setup scripts emit a clear warning if `npx` is missing. Acceptable: dotfiles install bootstraps Node anyway.
- **`npx skills` deploys to `~/.agents/skills/` for Codex** (a shared dir convention), not `~/.codex/skills/`. Codex's discovery is expected to read the shared dir; if a future Codex CLI version regresses, we'd need a fallback. No issue today.
- **One vendor's setup script can't deploy for another vendor** in a single run. `dotfiles agent-setup` invokes all three setup scripts sequentially, which is fine.
- **`npx skills` is third-party.** If `vercel-labs/skills` is abandoned, we'd need a replacement — but at 17k★ with active maintenance, that's a long horizon. Pinning a version (`npx skills@x.y.z`) is the mitigation if needed.

## What changed in this commit

- Deleted: `agents/{claude,cursor,codex}/skills/` and `agents/{claude,cursor,codex}/agents/` (mirror dirs, all symlinks).
- Moved: `agents/claude/skills/agents-overview/` → `.ai/skills/agents-overview/`.
- Modified: `agents/claude/setup.sh` and `agents/codex/setup.sh` to deploy via `npx skills add` for skills + small `cp` loop for subagents.
- Modified: `agents/shared/validate-skills.sh` — dropped legacy-vendor-agents section (no more legacy).
- Updated: `AGENTS.md`, `README.md`, `tests/test_scaffold.sh` to reference canonical paths.

## See also

- [ADR-0001](0001-canonical-skills-symlinked-into-vendors.md) — the previous pattern (superseded).
- `docs/specs/2026-05-07-skills-research.md` (local notes) — phased plan; this ADR records the architectural pivot found during Phase 5 review.
- `.ai/skills/skill-creator/references/skill-format.md` — author-side conventions (promoted out of `.ai/rules/process/` 2026-06-01).
- `.ai/skills/skill-creator/references/agent-format.md` — same for subagents (promoted 2026-06-01).
- [vercel-labs/skills](https://github.com/vercel-labs/skills) — the public CLI.
- [agentskills.io](https://agentskills.io) — skill spec we conform to.
