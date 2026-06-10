# Pi customization audit

> Last reviewed: 2026-06-10. Companion to [`docs/pi-power-setup.md`](../pi-power-setup.md). Focus: keep base Pi minimal, add sharp extension-level capabilities only when they reduce risk or context tax.

## Current Pi surfaces

| Surface | Current source | Assessment |
|---|---|---|
| Global instructions | `~/.pi/agent/AGENTS.md`, generated from `ai/agents/shared/rules.md` | Good. Shared kernel stays portable across the fleet. |
| Skills | `~/.agents/skills` for canonical repo skills; Pi packages also contribute package skills | Good base, but package skills create overlap. Prefer repo-owned process skills. |
| Subagents | `~/.pi/agent/agents`, deployed from `ai/subagents/` | Fine. Pi gets subagents via extension/package support, not base core. |
| Extensions | `ai/agents/pi/extensions/*.ts` plus package extensions from `pi-superpowers-plus` and `mitsupi` | Strongest customization surface. Our local set is useful but still thin. |
| Permissions | `permission-policy.ts` + `permission-policy.json`; `safe-git.ts` for git/gh prompts | Adequate terminal safety for git/gh. Not a sandbox. Zed/ACP does not bridge Pi prompts. |
| Status/footer | `git-status.ts` | Good canonical statusline. Missing 5h/7d split and context attribution. |
| Packages | `npm:pi-superpowers-plus`, `npm:mitsupi` in `ai/agents/pi/settings.json` | Useful, but both inject skills. Superpowers also injects workflow state/gates. |

## What Pi is doing behind the scenes

Pi's base harness is intentionally small: core tools plus loaded context from project/user instructions, skills, prompts, extensions, and active session history. We should generally trust the base context harness more than we should customize it: its value is low prompt tax and inspectable file-backed state.

Customize around the harness, not inside it:

- Use `AGENTS.md` for durable cross-agent behavior.
- Use skills for optional procedures and taste-heavy guidance.
- Use TypeScript extensions for deterministic behavior that should not cost model tokens: statuslines, permission gates, redaction, tool wrappers, session commands, and routing commands.
- Avoid always-on natural-language rules for things that can be enforced deterministically.

## Current package breakdown

### `pi-superpowers-plus`

Includes:

- Skills: `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `finishing-a-development-branch`, `using-git-worktrees`, `dispatching-parallel-agents`.
- Extensions: workflow monitor, plan tracker, subagent tool.

Assessment: useful enforcement ideas, but it is currently too much process authority for this repo. The stale workflow HUD is a symptom. Prefer owning the skills and selectively keeping only extension behavior we want.

### `mitsupi`

Includes:

- Skills: web/search/browser/github/uv/tmux/sentry/summarize/mermaid/etc.
- Extensions: `/answer`, `/btw`, context breakdown, files UI, split-fork, loop, multi-edit, notify, review, session breakdown, todos, uv helpers, prompt editor, whimsical status.

Assessment: more of a toolbox than a process framework. Good ideas to study or selectively in-source. `multi-edit`, context breakdown, split-fork, notify, session breakdown, and prompt editor are more interesting than most of the bundled skills.

## Skill collision audit

Added command:

```bash
dotfiles agent skills audit
```

It scans repo-owned skills against installed Pi package skills and flags conservative name/domain overlaps. Current notable collisions are expected:

- `tdd-vertical-slices` vs `test-driven-development`
- `diagnose` / `agentic-e2e-debugging` vs `systematic-debugging`
- `planning` / `collaborative-ideation` vs Superpowers planning/brainstorming
- `review` / `design-review` vs Superpowers code-review skills
- `browser-tooling` vs `web-browser`
- `github-workflow` / PR skills vs `github`
- `git-worktree-manager` vs `using-git-worktrees`

Recommendation: keep repo-owned process skills; in-source or drop package skills that compete.

## Cursor skill parity

Cursor was previously reporting only vendor built-ins under `~/.cursor/skills-cursor`. Setup now symlinks canonical skills into `~/.cursor/skills` from `ai/skills/`, and overview/verify count that owned skill surface instead of vendor built-ins.

## Extension roadmap, ranked

Build/keep:

1. `/consult` — second opinion primitive. Prefer this name over `/oracle`; `oracle` is not an industry term here and is too cryptic. `/consult` can later power `/review --consult`.
2. Context attribution footer/command — show what consumes context: transcript, files, tool output, skills, cache.
3. 5h/7d quota split — extend `git-status.ts` if provider headers expose both windows.
4. Output redaction — deterministic tool-output filter; near-zero model tax if implemented as an extension hook.
5. Hashline edit helper — optional robust edit path for large/churny files; do not replace simple string edits until proven.
6. LSP sidecar — read-only first (`diagnostics`, `references`, `definition`), because Zed remains the IDE.
7. `/handoff` — deterministic session closeout prompt generator.
8. `/decision` — durable decision capture into docs, not model memory.
9. `/review --consult` — structured multi-model/cross-model review after `/consult` exists.
10. Architecture guard — deterministic + heuristic checks for god files, helper sprawl, duplicate abstractions, and parallel implementations.
11. Model router — route by task class only after we have enough usage evidence.
12. Cost guard — budget/statusline warnings for paid models.
13. Browser-tooling router — command wrapper around the existing browser-tooling skill/tool choices.

Defer or sidecar:

- Kernels: useful for data/prototype sessions, but not core coding-agent behavior.
- DAP/debugger: keep in Zed or as an explicit sidecar; do not bloat Pi's default tool surface.
- Full sandboxing: worth evaluating separately. Extension permissions reduce mistakes; sandboxing contains damage. They solve different problems.

## Workflow closeout posture

Avoid overlapping closeout paths. Use one canonical closeout ladder:

1. During implementation: `plan_tracker` for task progress only.
2. Before claiming done: verification evidence from tests/builds.
3. Before merge/PR: `review` or `pr-greenlight-cycle` depending on whether CI/PR exists.
4. At session boundary: `workflow-closeout-learning` only for long sessions or when explicitly asked.
5. After crashes/parallel agents: `session-recovery` or `workspace-health-audit`, not normal closeout.

This keeps closeout situational instead of a mandatory ceremony on every task.
