# Add Pi power packages: mitsupi + a vendored safe-git guardrail

**Date**: 2026-05-25.
**Status**: accepted. Builds on [ADR-0005](0005-re-add-pi-as-local-first-agent.md).

## Context

[ADR-0005](0005-re-add-pi-as-local-first-agent.md) re-added Pi as a managed local-first terminal agent with one third-party package (`pi-superpowers-plus`). After researching power-user Pi setups, two additions stood out:

- **`mitsupi`** (npm, Armin Ronacher's `agent-stuff`) — the author-blessed canonical "amazing Pi" kit: `/review` (forks a session for peer review then merges findings), `/answer`, `/todos`, `/handoff`, `loop`, `notify`, plus ~19 skills. Armin uses Pi as his exclusive coding agent, so this is the reference workflow.
- **A git guardrail** — Pi has **no built-in permission system**, which is the one place it is weaker than Claude Code. The dotfiles "never run destructive git ops unless explicitly asked" rule had no harness-level enforcement in Pi.

The obvious guardrail candidate, `qualisero/rhubarb-pi`'s `safe-git`, is **not a clean package**: not on npm, installed via repo-local `npm run install:*` scripts, bundles five unrelated extensions, and its `index.ts` depends on a `../../shared` notification module. Installing it as-is would mean cloning a 10-star repo and running its build scripts with full permissions — against the dotfiles idempotent/owned/reviewable philosophy.

## Decision

- **Install `mitsupi`** as a managed npm package — added to `agents/pi/settings.json` `packages` and given its own opt-out block in `agents/pi/setup.sh`, mirroring `pi-superpowers-plus`.
- **Vendor `safe-git`, do not install it.** A single self-contained `agents/pi/extensions/safe-git.ts` is committed to the repo (MIT, attributed to qualisero/rhubarb-pi), with the `../../shared` notification machinery stripped — only the proven guardrail logic (pattern interception + approval prompts + session approve/block state + `/safegit*` commands) remains. `setup.sh` already symlinks every `*.ts` in `extensions/`, so it deploys with no extra wiring.
- **Enable safe-git at `promptLevel: "medium"`, `enabledByDefault: true`** via `settings.json` `safeGit`.

## Why

- **mitsupi is low-risk, high-signal** — a maintained npm package from the agent's most prominent power user; same install/opt-out shape as the already-accepted `pi-superpowers-plus`.
- **Vendoring safe-git keeps the dotfiles invariant**: the guardrail is owned, reviewable, version-controlled, and self-contained — no clone-and-build of a third-party repo, no notification dependency we don't want. It matches how `git-status.ts` is already handled.
- **Closes Pi's biggest gap vs. Claude Code** (no permission model) with a fail-safe: in headless/non-interactive mode the matched commands are **blocked entirely** rather than auto-run.

## Trade-offs accepted

- **safe-git blocks git/gh in headless mode.** ADR-0005 calls headless Pi (`pi -p`, RPC, SDK) a core use case. With safe-git enabled, matched git/gh commands are blocked when there is no UI. **Automation repos that need git in headless mode must set `"safeGit": { "enabledByDefault": false }` in their own `.pi/settings.json`.** This is the deliberate fail-safe direction — we'd rather an unattended run be blocked than silently force-push.
- **Vendored code drifts from upstream.** Our `safe-git.ts` won't pick up rhubarb-pi fixes automatically. Acceptable: it's ~250 lines of stable logic and we own it.
- **Two more full-permission third-party surfaces.** `mitsupi` runs arbitrary code with full permissions (opt-out by commenting its `setup.sh` block); `safe-git` is vendored so it's fully reviewable in-repo.
- **safe-git needs a live `/reload` smoke test** in an interactive Pi session before it's trusted — it was adapted (deletions only) but not runtime-verified in this environment.

## Considered and rejected

- **oh-my-pi** (`can1357/oh-my-pi`) — a heavy fork adding LSP, a DAP debugger, persistent execution, browser automation, and hashline edits. Rejected as the Pi slot: it abandons Pi's sub-1k-token / 4-tool minimalism, namespaces config into its own `~/.omp` (not our shared `~/.agents/skills` + `AGENTS.md`), and is a fast-churning solo-maintained fork. It hurts cross-agent consistency more than it helps. May be installed **side-by-side** under `~/.omp` for heavy refactor/debug sessions only — never as a drop-in Pi replacement. See `docs/pi-power-setup.md`.

## Revisit if

- safe-git's headless block proves too disruptive to automation → flip headless behavior to allow, or default `enabledByDefault: false`.
- mitsupi's `/review` overlaps confusingly with the canonical `premerge-review` skill → document which to reach for.
