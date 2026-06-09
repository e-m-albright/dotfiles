# Agent Fleet Uniformity

> **Last reviewed**: 2026-06-09 — Refresh when a vendor changes its config schema or a new agent joins the fleet.

We run five coding agents — **Claude Code, Codex, Cursor, Gemini, Pi** — from one set of dotfiles config (`ai/agents/`), deployed by the Python CLI (`dotfiles agent setup`). This doc records what "uniform" means across them, where it can't be (vendor limits), and how the two cross-cutting concerns — **statuslines** and **permissions** — are kept in sync.

The guiding rule: **one source of truth per concern, translated per vendor, drift-gated by a test.** Edit the canonical artifact; a test fails if a vendor file falls out of sync.

---

## Capability matrix (target state)

This table is the **single source of truth** — `cli/.../capability_matrix.py` mirrors it cell-for-cell, a drift test (`test_capability_matrix.py`) fails if they diverge, and `dotfiles agent overview` renders it **live** (probing what's actually deployed, so an unmet target shows as a gap, never a false green).

| Capability | Front-runner | Claude Code | Codex | Cursor | Gemini | Pi |
|---|---|---|---|---|---|---|
| Rules (instructions) | — | ✓ `CLAUDE.md` | ✓ `AGENTS.md` | ✓ `.mdc` | ✓ `GEMINI.md` | ✓ `AGENTS.md` |
| Skills | Claude | ✓ `.claude/skills` | ✓ `.agents/skills` | ✓ `skills-cursor` | ⊘ *(no skills surface)* | ✓ `.agents/skills` |
| Subagents | Claude | ✓ `.claude/agents` | ✓ `.codex/agents` | ✓ `.cursor/agents` *(2.4)* | ⊘ *(no subagents)* | ✓ `.pi/agent/agents` |
| MCP servers | Claude | ✓ `granola` | — | — | — | — *(by choice — local-first)* |
| Hooks | Claude | ✓ | ✓ | ✓ | ⊘ | ⊘ *(extensions instead)* |
| Statusline | Claude | ✓ `statusline.sh` | ✓ `statusline.toml` | ⊘ native UI | ⊘ native footer | ★ `git-status.ts` |
| Permissions | Claude | ✓ `permissions.json` | ⊕ `default.rules` + sandbox | ✓ `cli-config.json` | ✓ `tools.exclude` | ✓ `permission-policy.json` + presets |
| Plugins | Claude | ✓ `marketplace` | ⊘ *(no marketplace)* | — *(marketplace 2.5, GUI-managed)* | ⊘ | ⊘ |

Glyphs encode the **closable-vs-not-closable** axis: **✓** live · **✗** closable gap (the vendor supports it; we simply haven't deployed it — *ours* to close) · **⊘** unsupported (the vendor has no such surface yet — closable only by *their* tooling development) · **—** n/a by our choice (e.g. MCP everywhere but Claude) · **★** canonical (the Pi end-state we converge toward) · **⊕** different mechanism. **Front-runner** = who shipped the capability first (Claude Code usually leads, the others copy, and we decide what to own in Pi).

**MCP is intentionally near-zero** (June 2026 decision): only **granola** earns a server (semantic meeting-search has no CLI), on Claude alone. **context7 was retired for the `ctx7` CLI** (`npx ctx7 library <name>` / `ctx7 docs <id>` — full parity, universal across every shell-capable agent, no per-vendor patchiness, no always-on tax). So `mcp` is `✓` on Claude and `—` (our choice) elsewhere — zero closable gaps.

Only the **terminal** agents (Claude, Codex, Pi) can render a custom statusline. Cursor and Gemini use their own status UI and are out of scope for statusline alignment.

---

## The fifth slot: Gemini → Antigravity (decided 2026-06-09)

**Decision: drop Gemini CLI, migrate the fifth fleet slot to Google's Antigravity CLI (`agy`).** Google is [transitioning Gemini CLI to Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); **on 2026-06-18 Gemini CLI stops serving Pro/Ultra/free individual users.** Antigravity also closes Gemini's old gaps — it ships **Skills, Subagents, Hooks, and Plugins** (Gemini Extensions rebranded), so the fifth slot goes from the weakest column to near-parity.

**Status: installed + config migrated; registry-label rename pending.** `agy` is installed (brew cask `antigravity-cli` → `/opt/homebrew/bin/agy`, v1.0.6) and **verified to read the same `~/.gemini/` config as Gemini CLI** — so the migration is mostly a binary swap. Done: package source (`gemini-cli` → `antigravity-cli`); the vendor now checks for `agy` and writes the portable **`~/.gemini/AGENTS.md`** (retiring `GEMINI.md`); MCP + `tools.exclude` permissions already land in `~/.gemini/settings.json` which `agy` reads. The vendor key stays `gemini` (driving `agy`) until the cosmetic registry rename — deferred only to avoid clobbering an in-flight `cli.py` edit by a parallel agent.

Verified config (live on this machine):

| Surface | Config | Status |
|---|---|---|
| Install | brew cask `antigravity-cli` → `agy` (auto-updates) | ✅ done |
| Home dir | **`~/.gemini/`** (same as Gemini CLI — settings.json, config/, oauth_creds.json…) | ✅ verified |
| Global instructions | **`~/.gemini/AGENTS.md`** (portable; `agy` reads AGENTS.md + GEMINI.md, GEMINI.md outranks — we deploy AGENTS.md and delete GEMINI.md so it's authoritative). **GEMINI.md is not dead, just unused by us.** | ✅ done |
| MCP | `~/.gemini/settings.json` `mcpServers` (same schema) — currently empty by choice (MCP is Claude-only) | ✅ done |
| Permissions | `~/.gemini/settings.json` `tools.exclude` (deny-vocab) | ✅ done |
| Plugins | `agy plugin import gemini` / `agy plugin install <x>@<mp>` | available |
| Skills · Subagents · Hooks | `agy` **supports** all three (global skills `~/.gemini/antigravity-cli/skills/`, `/agent`, JSON hooks) but the on-disk paths aren't yet confirmed — **not wired** | ⚠️ pending |

**Remaining steps:** (1) rename the `gemini` vendor → `antigravity` in `dotfiles.agent.VENDORS` + the matrix/`_SURFACE_MAP`/`_AgentChoice` keys (do once `cli.py` is clear); (2) verify the skills/subagents/hooks on-disk paths on the live `agy` and wire them (flipping those matrix cells from `⊘` to `✓`); (3) the matrix column relabels gemini→antigravity. The `dotfiles agent web copy` Gemini-*web*-chat command is unrelated and stays.

Sources: [transitioning blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) · [Antigravity subagents/skills](https://developers.googleblog.com/subagents-have-arrived-in-gemini-cli/) · Gemini CLI v0.26.0 (Skills/Hooks/Subagents) · gemini-cli issue #16058.

---

## Recently adopted capabilities (June 2026 landscape sweep)

What shipped across the tools lately, with our verdict. KEEP/adopt = part of the toolkit; evaluate/skip = parked with reason.

| Capability | Tool | Verdict | How we use it |
|---|---|---|---|
| **Dynamic Workflows** — JS orchestration script the agent writes + a runtime runs; fans out to ≤1000 subagents, results stay out of context, built-in adversarial cross-check | Claude Code | **KEEP** | the right primitive for codebase-wide audits/migrations/research in this repo (orchestration as code you own + rerun). Trigger via the `workflow` keyword or ultracode. |
| **`/usage`** — per-category token breakdown (skills / subagents / plugins / per-MCP) | Claude Code | **KEEP** | the empirical input to every context-trim decision — tells you which substrate actually costs tokens, instead of guessing. |
| **`--safe-mode`** (`CLAUDE_CODE_SAFE_MODE`) — disables CLAUDE.md / plugins / skills / hooks / MCP | Claude Code | **KEEP** | harness troubleshooting — bisect whether our config or the base agent is the problem. |
| **`.agents/skills/`** as the canonical cross-vendor skills path | Codex · Pi · Cursor(read) | **adopted** | already where our `npx skills` pipeline lands shared skills; the emerging portable standard. |
| Named permission profiles + `auto_review` reviewer | Codex | **evaluate** | aligns with our `ai/.agents/` permission-profile model; revisit when we formalize Codex profiles. |
| Auto-review Run Mode, SDK custom tools | Cursor | **skip** | only relevant if we script Cursor headless, which we don't. |
| Subagents (2.4) + plugin marketplace (2.5) | Cursor | **adopted (subagents)** | our 5 subagents now deploy to `~/.cursor/agents`; the marketplace stays GUI-managed (not fleet state). |

---

## Statuslines — Pi is canonical

Pi's `git-status.ts` footer is the reference design: a warm **amber/sage** ramp (burnt amber under pressure, sage when there's headroom — never alarm red), auth-class cost (`local` / `sub %` / `api $`), granular git (staged/unstaged/untracked/conflicts/ahead/behind), and a two-line layout.

The shared **visual language** is the amber/sage ramp, identical tiers everywhere:

| Tier | Color | Threshold |
|---|---|---|
| burnt amber | `#d9784d` | ≥ 90% |
| amber | `#d9913d` | ≥ 75% |
| gold | `#d3b15f` | ≥ 55% |
| sage | `#8fa879` | < 55% |

- **Pi** (`ai/agents/pi/extensions/git-status.ts`) — the reference. `amberRamp()` defines the tiers.
- **Claude** (`ai/agents/claude/statusline.sh`) — `ramp()` retuned to the exact same tiers/colors. Keeps Claude's richer 5h/7d rate-limit split (its payload exposes both windows).
- **Codex** (`ai/agents/codex/statusline.toml`) — segment set matches the canonical info (project · git · model · context% · 5h · 7d · fast-mode). Codex only exposes a theme name, not per-segment colors, so the palette can't be matched; the segments carry the uniformity.

**Idea on deck (not yet built):** give Pi the 5h + 7d split Claude has, when the active provider exposes both rate-limit windows in response headers. Today Pi shows a single quota %. This depends on Pi surfacing the relevant provider headers (confirmed for `openai-codex`; unverified for Anthropic-OAuth), so it's parked until that's checked.

---

## Permissions — one vocabulary, two surfaces

### The canonical deny vocabulary

`ai/agents/shared/deny-commands.yaml` is the single source of truth for the universal **hard-stop** commands (rm -rf, sudo, dd, mkfs, chmod 777, git push --force, git reset --hard, git clean, git branch -D, curl|sh, killall, fork bomb, …). Each entry lists the exact string for each surface that should carry it; the syntaxes differ (glob vs regex vs prefix), so we hand-author each vendor file rather than machine-translate security-critical patterns.

The drift gate — `cli/src/dotfiles/cmd/agent/test_deny_commands_sync.py` — parses every vendor config and fails if a canonical string is missing. **To add a hard stop:** add it to the YAML, then add the named per-surface string to each vendor file the test points you at.

Surfaces and where they land:

| Surface | File | Form |
|---|---|---|
| claude | `ai/agents/claude/permissions.json` `.deny[]` | `Bash(<prefix>:*)` |
| cursor | `ai/agents/cursor/cli-config.json` `.permissions.deny[]` | `Shell(<cmd>)` |
| zed | `editors/zed/settings.json` terminal `always_deny[].pattern` | regex |
| pi | `ai/agents/pi/permission-policy.json` `.denyCommands[].patterns` | regex |
| gemini | `ai/agents/gemini/settings.json` `tools.exclude[]` | `run_shell_command(<prefix>)` |

Pi is intentionally a **superset** (its preset-driven policy denies these and more); the test only checks the floor is present. Gemini's `exclude` is prefix-only (can't target git sub-flags), so it carries the catastrophic top-level commands only. Pipe-to-shell and the fork bomb are expressible only on the regex surfaces (Zed/Pi), so Claude/Cursor/Gemini rely on the model + their default mode there.

### Two enforcement surfaces

This is the part that surprises people: **the config that governs approvals depends on how you launch the agent.**

1. **Standalone / terminal** — each agent's own config is authoritative. Pi's `permission-policy.json` gates fire, Claude reads `permissions.json`, Codex reads `config.toml` (`approval_policy` + `sandbox_mode`) and `default.rules`, Cursor reads `cli-config.json`, Gemini reads `tools.exclude`.

2. **Inside Zed (ACP)** — Zed is the client and **Zed decides**. The agent calls `session/request_permission`; Zed renders the prompt and auto-resolves it from `editors/zed/settings.json` → `agent.tool_permissions`. Evaluation order: built-in security → `always_deny` → `always_allow` → per-tool `default`. We keep `terminal.default: "allow"` (fast flow) and add an `always_deny` floor mirroring the canonical vocabulary.

### Zed gotchas (confirmed 2026-06-01)

- **Codex via Zed overrides your `config.toml`.** The embedded engine still enforces `sandbox_mode` and runs `default.rules` logic, but under ChatGPT auth Zed pins `approval_policy = on-request` / `sandbox_mode = workspace-write`, and the interactive prompt is Zed's UI. So your `config.toml` `approval_policy` is largely ignored when driving Codex from Zed — Zed's `tool_permissions` + session mode are what actually gate.
- **Pi via Zed has no approval bridge.** Pi runs through the community `pi-acp` adapter (`pi --mode rpc`), which does **not** call `session/request_permission`. Pi's `ask` gates run inside the subprocess and never surface to Zed. If you need Pi's permission gates to actually prompt, **run Pi in a terminal**, not through Zed.

Sources: Zed external-agents & tool-permissions docs (`zed.dev/docs/ai/*`), ACP spec (`agentclientprotocol.com/protocol/tool-calls`), `zed-industries/codex-acp`, `svkozak/pi-acp`, OpenAI Codex approvals docs.

### Claude allow-list posture

Claude's `permissions.json` keeps a broad `allow` for inner-loop dev commands (auto-approved) but **does not** auto-approve outward-facing/publish/deploy/auth mutations — `gh pr merge`, `gh pr close`, `gh release create`, `gh repo fork`, `gh auth`, `gh api`, `wrangler` prompt instead. Catastrophic variants (force-push, hard reset, rm -rf, …) are in `deny`.

---

## Hooks — one intent set, three events per vendor

Hooks are **deterministic, harness-side automation** fired at lifecycle points. The key property: **they cost the model zero context** (they're shell commands the harness runs, not tokens the model reads), so unlike rules/MCP they aren't a budget concern — they're pure "make the floor deterministic." We run **one canonical intent set**; only the event *name* and *script* differ per vendor (each harness hands a different payload, so the scripts can't be literally shared).

| Intent | Claude | Codex | Cursor | Gemini→agy | Pi |
|---|---|---|---|---|---|
| **Guard** destructive git/file ops | `PreToolUse` → `git-guardrails.sh` + path guard | `PreToolUse` (inline glob) | `beforeShellExecution` → `guard-destructive.sh` | ⚠️ pending | `safe-git` extension |
| **Format** on file edit | `PostToolUse` → `format-on-save.sh` | `PostToolUse` → `format-on-save.sh` | `afterFileEdit` → `format-on-save-shim.sh` | ⚠️ pending | — |
| **Notify** on done/idle | `Stop`+`Notification` → terminal bell | `Stop` → `terminal-notifier` | — | ⚠️ pending | — |

**Deliberate divergences (not drift):**
- **Notify is the loosest** intent — Claude rings the bell (universal, guarded by `$CURSOR_AGENT` so it's silent inside Cursor), Codex uses `terminal-notifier` (richer, needs the brew package), Cursor skips it. Acceptable: notify is quality-of-life, not a safety floor.
- **Guard is the floor** and is everywhere it can be — the three hook-capable terminal agents plus Pi's `safe-git` extension. This is the same hard-stop posture as the [deny vocabulary](#permissions--one-vocabulary-two-surfaces), enforced a second way (at tool-call time, not just config).
- **Gemini→agy hooks are pending** — `agy` supports a JSON hook lifecycle, but the on-disk path isn't yet confirmed; wire guard+format there when verified (closing those ⚠ cells).

**To change a hook:** edit the per-vendor script (`ai/agents/<vendor>/hooks/`); the intent set above is the contract each vendor must satisfy. New hard-stop guard patterns belong in `deny-commands.yaml` *first* (the config floor), then the guard hook is the runtime backstop.

---

## Adding a new agent to the fleet

1. Add a `setup_<vendor>()` module under `cli/src/dotfiles/cmd/agent/vendors/`.
2. Deploy rules (`build_global_instructions` → its instruction file), MCP (`mcp_servers_for`), subagents (`deploy_subagents` if it reads an agents dir), and a permission posture.
3. If it can express a deny list, add it as a surface in `deny-commands.yaml` + `deny_commands.py` (`SURFACES`, `SURFACE_FILES`, `deny_strings_in_config`), and hand-author the strings — the drift test will hold it in sync.
4. If it supports hooks, satisfy the canonical intent set (guard / format / notify) via its event names; map them in the [Hooks](#hooks--one-intent-set-three-events-per-vendor) table.
5. Add it to the [capability matrix](#capability-matrix-target-state) (and `capability_matrix.py` + the drift test) so its surfaces are tracked.
6. If it runs through Zed/ACP, remember the two-surface rule: its in-Zed approvals are governed by `editors/zed/settings.json`, not its own config.
