# Pi power setup

Reference for the [Pi coding agent](https://pi.dev) as managed in this repo (`agents/pi/`), the repo-owned extensions we run, and the standing **oh-my-pi vs. base Pi** decision. Decisions live in [ADR-0005](adr/0005-re-add-pi-as-local-first-agent.md) and [ADR-0006](adr/0006-pi-power-packages-mitsupi-and-safe-git.md); this is the practical companion. See also the current customization audit: [`docs/knowledge/pi-customization-audit.md`](knowledge/pi-customization-audit.md).

## What Pi is

A minimal, aggressively-extensible terminal coding agent by Mario Zechner (badlogic / earendil-works). Headline traits:

- **Sub-1k-token system prompt; 4 core tools** (Read, Write, Edit, Bash). Everything else is an extension/skill.
- **Hot-reloadable TypeScript extensions** — `/reload` re-loads extensions, skills, prompts, keybindings, and `AGENTS.md` without a restart.
- **Mid-session provider/model swap**, session trees, headless modes (`pi -p`, `--mode rpc`, SDK).
- It's the harness under Peter Steinberger's OpenClaw and Armin Ronacher's daily driver.

Docs: [pi.dev/docs](https://pi.dev/docs/latest) · monorepo [earendil-works/pi](https://github.com/earendil-works/pi) (moved from `badlogic/pi-mono`; old URL still redirects) · curated [awesome-pi-agent](https://github.com/qualisero/awesome-pi-agent). Current: **v0.79.0** (2026-06).

## How it plugs into our multi-agent fleet (the key advantage)

Pi inherits our shared config for free — no Pi-specific duplication:

- **Skills**: Pi natively reads `~/.agents/skills/` (the Codex dir our `npx skills` pipeline populates). Every `ai/skills/` skill — including `review` — shows up in Pi after `dotfiles agent setup`.
- **Context**: Pi loads `AGENTS.md` the same way Codex does; the shared `rules.md` kernel is the single source, inlined by `dotfiles agent setup`.
- **Subagents**: map to `~/.pi/agent/agents/*.md` via the shared deployer.

Keep using `~/.agents/skills` + `AGENTS.md` as the canonical sources — that's what makes the fleet behave consistently.

## Extensions we run

External Pi packages are intentionally disabled by default. We own the process skills in `ai/skills/` and keep Pi's runtime surface small; third-party packages are reference material, not active workflow authorities.

| Name | Type | Source | What it gives us |
|------|------|--------|------------------|
| `safe-git` | vendored extension | `agents/pi/extensions/safe-git.ts` | Approval gate for destructive git/gh — Pi's missing permission model |
| `git-status.ts` | vendored extension | `agents/pi/extensions/git-status.ts` | Git-aware footer status |
| `permission-policy.ts` | vendored extension | `agents/pi/extensions/permission-policy.ts` | Regex/preset policy gate from `permission-policy.json` |
| `presets.ts` | vendored extension | `agents/pi/extensions/presets.ts` | Named Pi presets from `presets.json` |

Previously evaluated but now disabled: `pi-superpowers-plus` (too much process authority / stale workflow state) and `mitsupi` (useful toolbox, but it injects overlapping skills/extensions). In-source only the pieces we decide to own.

### safe-git — usage & the headless caveat

Pi has no built-in permission system; `safe-git` intercepts bash calls and gates git/gh.

- **Levels** (`settings.json` → `safeGit.promptLevel`): `high` (force push, hard reset, clean, branch delete, stash drop, reflog expire), `medium` (the above + push, commit, rebase, merge, tag, cherry-pick, revert, all `gh`), `none` (off). Default: **medium**.
- **Per-session controls**: `/safegit` (toggle), `/safegit-level <high|medium|none>`, `/safegit-status`. Each prompt offers approve-once / decline / auto-approve-this-type / auto-block-this-type for the session.
- **⚠️ Headless behavior**: in non-interactive mode (`pi -p`, RPC, SDK) matched commands are **blocked entirely** — the deliberate fail-safe. **If an automation repo needs git in headless Pi, set `"safeGit": { "enabledByDefault": false }` in that repo's `.pi/settings.json`.**
- Vendored & adapted (notification deps stripped) from [qualisero/rhubarb-pi](https://github.com/qualisero/rhubarb-pi) (MIT). Needs a live `/reload` smoke test before fully trusting it.

### Worth evaluating later

- `/consult` is now repo-owned (`ai/agents/pi/extensions/consult.ts`): second opinion from Claude/Codex without installing `oracle`. Keep watching external implementations only for ideas.
- `filter-output` / `security` (michalvavra/agents) — redact tokens/secrets from tool output.
- Status-bar packages (`pi-powerline-footer`, `rytswd/pi-agent-extensions`) add subscription-usage + context-window display — feature ideas for our custom `git-status.ts`.

## Pi capability roadmap — owning the end state

Pi is our **canonical ideal agent**: smallest context tax, capabilities where they matter, no cruft. This is the decided list of what to build/keep, derived from the [capability matrix](knowledge/agent-fleet.md) front-runner column (where Claude Code leads and Pi should catch up) cross-referenced with the verified oh-my-pi / extension research below. Re-rank as the landscape moves.

| Capability Claude front-ran | Pi today | Decision | Source / how |
|---|---|---|---|
| **Permissions** | ✓ `safe-git` + permission-policy | **Shipped** — keep | vendored `safe-git.ts` is Pi's missing permission model; matrix shows ✓ |
| **Statusline rate-limit split (5h/7d)** | single quota % | **Parked** — build when Pi exposes both provider windows in response headers (confirmed for `openai-codex`, unverified for Anthropic-OAuth) | extend `git-status.ts` `quotaFromHeaders` |
| **MCP** | none | **Won't build** — local-first is the point; stays `· n/a by choice`, not a gap | — |
| **Hooks** | extensions | **Sufficient** — Pi's hot-reloadable extensions ARE its hook/automation surface; no `hooks.json` adapter needed | — |
| **Second opinion** (consult Claude/Codex mid-task) | ✓ `/consult` | **Shipped** — keep small/read-only; default Claude, `--codex` available | `ai/agents/pi/extensions/consult.ts` |
| **Output redaction** (secrets/tokens) | — | **Evaluate** — defense-in-depth for tool output | `filter-output`/`security` (michalvavra/agents) |
| **Robust large-file edits** | string-replace | **Defer** — only if Edit-churn becomes painful; test on our models first | oh-my-pi hashline (side-by-side `~/.omp`) |
| **IDE replacement** (LSP rename, DAP debug, kernels) | — | **Side-car only** — never in the fleet Pi slot (abandons minimalism); run oh-my-pi under `~/.omp` for refactor/debug sessions | `mise use -g github:can1357/oh-my-pi` |

The throughline: **own what raises quality at low context cost (permissions, second-opinion, redaction, statusline), refuse what trades away the sub-1k-token minimalism that is Pi's whole advantage (32-tool harnesses, MCP, IDE bloat).** When a "build"/"evaluate" item is acted on, move it into "Packages & extensions we run" and flip the matrix cell.

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

[oh-my-pi repo](https://github.com/can1357/oh-my-pi) · [CHANGELOG](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/CHANGELOG.md) · [DeepWiki hashline](https://deepwiki.com/can1357/oh-my-pi/8.1-hashline-mode) / [config](https://deepwiki.com/can1357/oh-my-pi/13-configuration-reference) · [self.md review](https://self.md/tools/oh-my-pi/) · base Pi [pi.dev](https://pi.dev) / [README](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md)
