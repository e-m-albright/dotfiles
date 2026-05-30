# Pi power setup

Reference for the [Pi coding agent](https://pi.dev) as managed in this repo (`agents/pi/`), the packages we run, and the standing **oh-my-pi vs. base Pi** decision. Decisions live in [ADR-0005](adr/0005-re-add-pi-as-local-first-agent.md) and [ADR-0006](adr/0006-pi-power-packages-mitsupi-and-safe-git.md); this is the practical companion.

## What Pi is

A minimal, aggressively-extensible terminal coding agent by Mario Zechner (badlogic / earendil-works). Headline traits:

- **Sub-1k-token system prompt; 4 core tools** (Read, Write, Edit, Bash). Everything else is an extension/skill.
- **Hot-reloadable TypeScript extensions** — `/reload` re-loads extensions, skills, prompts, keybindings, and `AGENTS.md` without a restart.
- **Mid-session provider/model swap**, session trees, headless modes (`pi -p`, `--mode rpc`, SDK).
- It's the harness under Peter Steinberger's OpenClaw and Armin Ronacher's daily driver.

Docs: [pi.dev/docs](https://pi.dev/docs/latest) · monorepo [badlogic/pi-mono](https://github.com/badlogic/pi-mono) · curated [awesome-pi-agent](https://github.com/qualisero/awesome-pi-agent).

## How it plugs into our multi-agent fleet (the key advantage)

Pi inherits our shared config for free — no Pi-specific duplication:

- **Skills**: Pi natively reads `~/.agents/skills/` (the Codex dir our `npx skills` pipeline populates). Every `.ai/skills/` skill — including `premerge-review` — shows up in Pi after `dotfiles agent-setup`.
- **Context**: Pi loads `AGENTS.md` the same way Codex does; `bake-rules.sh` is the single source.
- **Subagents**: map to `~/.pi/agent/agents/*.md` via the shared deployer.

Keep using `~/.agents/skills` + `AGENTS.md` as the canonical sources — that's what makes the fleet behave consistently.

## Packages & extensions we run

| Name | Type | Source | What it gives us |
|------|------|--------|------------------|
| `pi-superpowers-plus` | npm package | ADR-0005 | Superpowers port: TDD/verification gating + subagents (parity with Claude superpowers) |
| `mitsupi` | npm package | ADR-0006 | Armin Ronacher's kit: `/review`, `/answer`, `/todos`, `/handoff`, `loop`, `notify`, ~19 skills |
| `permission-policy` | vendored extension | `agents/pi/extensions/permission-policy.ts` + `agents/pi/permission-policy.json` | Deterministic blocklist for dangerous bash commands and protected paths |
| `presets` | vendored extension | `agents/pi/extensions/presets.ts` + `agents/pi/presets.json` | `/preset read`, `/preset safe-auto`, and `/preset dev` tool/instruction profiles |
| `safe-git` | vendored extension | `agents/pi/extensions/safe-git.ts` | Legacy approval gate for destructive git/gh. Mostly superseded by `permission-policy` while the policy is strict |
| `git-status.ts` | vendored extension | `agents/pi/extensions/git-status.ts` | Git-aware footer status |

### Permission policy and presets

Pi does not have Claude Code-style native permissions. We emulate the safe part with a deterministic extension, not model judgment:

- **Policy source**: `agents/pi/permission-policy.json`, symlinked to `~/.pi/agent/permission-policy.json` by `dotfiles agent-setup`. A project can add `.pi/permission-policy.json`; project rules are merged on top.
- **Default behavior**: allow commands unless a deny rule or protected path matches. The deny list is intentionally conservative: privileged shell, filesystem mutation, curl/wget, process control, state-changing git/GitHub, dependency installs, migrations, Docker/deploy mutation, and inline interpreter escape hatches.
- **Protected paths**: `.env*`, secrets folders, key/token/credential paths, `~/.ssh`, `~/.aws`, `~/.config/gh`, `.git`, and `node_modules` are blocked for `read`, `write`, `edit`, and bash mentions.
- **Status**: `/permissions-status` shows the active merged policy summary.
- **Presets**: `agents/pi/presets.json`, symlinked to `~/.pi/agent/presets.json`. `settings.json` sets `defaultPreset` to `dev`. Use `/preset read`, `/preset safe-auto`, or `/preset dev` to switch tools and append matching behavior instructions.

Reviewer-model approval is not native in Pi. It can be built as another extension using provider APIs or Pi's SDK, but keep it as a second opinion after deterministic allow/deny. A malformed or uncertain reviewer response should block or ask a human, never override the policy.

### safe-git legacy note

`safe-git` still exists as a session-level prompt gate, but the stricter `permission-policy` extension now blocks the same state-changing git/gh classes before `safe-git` can prompt. Keep `safe-git` around as a fallback while tuning the deterministic policy.

### Worth evaluating later

- `oracle` (hjanuschka/shitty-extensions) — second-opinion from another model; lets Pi consult our Claude/Codex subscriptions mid-task.
- `filter-output` / `security` (michalvavra/agents) — redact tokens/secrets from tool output.
- Status-bar packages (`pi-powerline-footer`, `rytswd/pi-agent-extensions`) add subscription-usage + context-window display — feature ideas for our custom `git-status.ts`.

## oh-my-pi vs. base Pi — decision

**Verdict: stay on base Pi for the fleet slot.** oh-my-pi ([can1357/oh-my-pi](https://github.com/can1357/oh-my-pi)) is genuinely impressive but solves a different problem.

### What oh-my-pi is

A **fork** by Can Bölük, MIT, created 2025-12-31 (~5 months old, ~7.3k stars) vs. base Pi's company-backed ~54k. Effectively a rewrite: TypeScript core **plus ~27k lines of Rust** (search, shell, AST, PTY, BPE counting in-process). Install `curl -fsSL https://omp.sh/install | sh`. **~30+ releases in ~13 days** — strong momentum *and* churn. No documented upstream-merge cadence; it's become its own product line.

### What it actually adds (verified)

| Feature | Real? | Note |
|---------|-------|------|
| Hashline edits (`LINEHASH\|TEXT`, 3-way stale-anchor recovery) | ✅ novel | Fundamentally different edit tool than Pi's string-replace |
| "61% fewer tokens" | ⚠️ marketing | Model-specific (Grok 4 Fast); vendor self-report, no independent harness |
| LSP (13 ops), DAP debugger (27 ops; lldb/dlv/debugpy) | ✅ | "Ask for a rename, get a rename" |
| Persistent Python/JS kernels, stealth browser/Electron automation | ✅ | |
| Schema-validated subagents (isolated worktrees) | ✅ | |
| Reads 8 config formats (Cursor MDC, Cline, Codex AGENTS.md, Copilot…) | ✅ | One-time *import* into `~/.omp`, not a live read |
| **32 tools, 40+ providers, 14 search backends** | ✅ | vs. base Pi's **4 core tools** |

### Why not for us

1. **It abandons Pi's minimalism on purpose.** 32 built-in tools ⇒ a far larger system prompt than Pi's sub-1k tokens. We lose the context-budget advantage that is Pi's headline feature. An [independent review](https://self.md/tools/oh-my-pi/) rates it "Mixed" for anyone wanting a quiet, locked-down assistant — "the point of the project is a powerful harness."
2. **It breaks fleet consistency.** Config lives in its own `~/.omp/` namespace (`config.yml`, `RULES.md`), **not** our shared `~/.agents/skills` + `AGENTS.md`. No evidence it reads `~/.agents/skills` at all; its config discovery is vendor-`.dot`-folder oriented and pulls config *toward* `.omp`. oh-my-pi would become the odd one out in the fleet.
3. **Churn / bus-factor.** Solo maintainer, daily breaking changes (renamed `pi://`→`omp://`, restructured `eval`, swapped TypeBox→Zod shim, remapped plugin scopes). Base Pi extensions aren't guaranteed to load unmodified.

### When it *would* be worth it

If you want Pi to **replace your IDE + debugger** (live LSP rename/diagnostics, real DAP debugging, persistent kernels, browser automation) or do heavy large-file editing where hashline reliability matters (test on your own models). In that case: install it **side-by-side under `~/.omp`** for refactor/debug sessions only — `mise use -g github:can1357/oh-my-pi` to pin — and never as a drop-in for the fleet Pi slot. The two coexist fine on disk.

### Sources

[oh-my-pi repo](https://github.com/can1357/oh-my-pi) · [CHANGELOG](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/CHANGELOG.md) · [DeepWiki hashline](https://deepwiki.com/can1357/oh-my-pi/8.1-hashline-mode) / [config](https://deepwiki.com/can1357/oh-my-pi/13-configuration-reference) · [self.md review](https://self.md/tools/oh-my-pi/) · base Pi [pi.dev](https://pi.dev) / [README](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md)
