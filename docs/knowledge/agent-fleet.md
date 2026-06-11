# Agent Fleet Uniformity

> **Last reviewed**: 2026-06-11 — Refresh when a vendor changes its config schema or a new agent joins the fleet. (`audit-agent-fleet-drift` re-proves this on a weekly cadence.)

We run five coding agents — **Claude Code, Codex, Cursor, Gemini, Pi** — from one set of dotfiles config (`ai/agents/`), deployed by the Python CLI (`dotfiles agent setup`). This doc records what "uniform" means across them, where it can't be (vendor limits), and how the two cross-cutting concerns — **statuslines** and **permissions** — are kept in sync.

The guiding rule: **one source of truth per concern, translated per vendor, drift-gated by a test.** Edit the canonical artifact; a test fails if a vendor file falls out of sync.

---

## Capability matrix (vendor support — provenance-backed)

This is the **VENDOR-CAPABILITY** matrix: does each tool *support* the capability? It's the single source of truth — `capability_matrix.py` mirrors it cell-for-cell, a drift test fails if they diverge, and **every supported cell carries a receipt** (a probe that proves it on this machine, and/or a source URL — see the Receipts table). Run the probes with `dotfiles agent capabilities --verify`. *(What WE have deployed/active is the per-agent checklist in `dotfiles agent overview`, a separate layer.)*

Status tokens: **yes** = generally available · **beta** = preview/partial/auto-only · **ext** = only via an extension (Pi) · **no** = proven absent (with evidence) · **unverified** = no first-party source AND not locally probeable. Reconciliation rule: when a local probe and a doc disagree, **the probe wins** (it's what's installed).

| Capability | Claude | Codex | Cursor | Antigravity | Pi |
|---|---|---|---|---|---|
| rules | yes | yes | yes | yes | yes |
| skills | yes | yes | yes | yes | yes |
| subagents | yes | yes | yes | yes | ext |
| mcp | yes | yes | yes | yes | no |
| hooks | yes | yes | yes | yes | ext |
| statusline | yes | yes | beta | yes | ext |
| permissions | yes | yes | yes | yes | ext |
| plugins | yes | yes | yes | yes | yes |
| dynamic-workflows | yes | no | unverified | no | yes |
| memory | yes | beta | unverified | yes | yes |
| output-styles | beta | yes | no | no | yes |
| slash-commands | yes | yes | yes | yes | yes |
| sandboxing | yes | yes | yes | yes | no |
| model-routing | yes | yes | beta | beta | beta |

**Proven absences** (`no` with positive evidence, not "didn't find"): Pi MCP ("No MCP" by design, README); Pi sandboxing ("Pi does not include a built-in sandbox" — use Docker); Codex dynamic-workflows (`js_repl` removed, `code_mode` WIP); Antigravity dynamic-workflows (its `/workflow` is markdown step-guides, not JS orchestration); Antigravity + Cursor output-styles (no style surface). The **agy `⊘`→`yes` corrections** (skills/subagents/hooks/statusline) were proven by the installed binary's own strings — see Receipts.

### Receipts (probe / source per supported cell)

The full per-cell provenance lives in `capability_matrix.py` (the `test` = on-machine probe, `src` = source URL) and prints via `dotfiles agent capabilities`. Examples of the on-machine probes: `strings $(which agy) | grep -qi 'Toggle the statusline'` (agy statusline), `strings $(which claude) | grep -qi 'dynamic workflow'` (Claude dynamic-workflows), `pi --help | grep -- --skill` (Pi skills), `claude mcp list` (Claude MCP). `--verify` runs them all and reports proven/failed.

**MCP is intentionally near-zero in OUR deployment** (separate from vendor support above): only **granola** earns a server (semantic meeting-search has no CLI), on **Claude + Codex**; **context7 was retired for the `ctx7` CLI** and is auto-pruned on setup (`disabled_mcp_server_names` → `merge_managed_mcp(prune=…)`).

---

## The fifth slot: Gemini → Antigravity (decided 2026-06-09)

**Decision: drop Gemini CLI, migrate the fifth fleet slot to Google's Antigravity CLI (`agy`).** Google is [transitioning Gemini CLI to Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); **on 2026-06-18 Gemini CLI stops serving Pro/Ultra/free individual users.** Antigravity also closes Gemini's old gaps — it ships **Skills, Subagents, Hooks, and Plugins** (Gemini Extensions rebranded), so the fifth slot goes from the weakest column to near-parity.

**Status: installed (v1.0.7) + rules/MCP/permissions wired & verified; UI relabeled to Antigravity/`agy`.** `agy` is installed (brew cask `antigravity-cli` → `/opt/homebrew/bin/agy`) and **verified to read the same `~/.gemini/` config as Gemini CLI** — so the migration was a binary swap. The vendor checks for `agy` and writes the portable **`~/.gemini/AGENTS.md`** (retiring `GEMINI.md`); MCP + `tools.exclude` permissions land in `~/.gemini/settings.json` which `agy` reads. The internal vendor key stays `gemini` **on purpose** — it's literally agy's config dir (`~/.gemini`); the display name is **Antigravity** and the matrix column shows **`agy`**.

Verified config (probed live on v1.0.7):

| Surface | Config | Status |
|---|---|---|
| Install | brew cask `antigravity-cli` → `agy` v1.0.7 (auto-updates) | ✅ done |
| Home dir | **`~/.gemini/`** (settings.json, config/, antigravity-cli/, oauth_creds.json…) | ✅ verified |
| Global instructions | **`~/.gemini/AGENTS.md`** (we deploy it; GEMINI.md deleted) | ✅ done |
| MCP | `~/.gemini/settings.json` `mcpServers` + an (empty) `~/.gemini/config/mcp_config.json` agy now seeds — empty by choice (MCP is Claude-only) | ✅ done |
| Permissions | `~/.gemini/settings.json` `tools.exclude` (deny-vocab) | ✅ done |
| Plugins | `agy plugin import gemini\|claude` / `install <x>@<mp>` | available |
| Skills | **`~/.gemini/antigravity-cli/skills/`** (global, SKILL.md standard — same as the fleet); we symlink the canonical set there via `_setup_skills` | ✅ done |
| Subagents | **Programmatic, not file-deployed** — agy spawns subagents dynamically (built-in roles / generic clones / on-the-fly registration), no `.md`-dir to drop into. Workspace `.agents/` agent-scripts are per-repo, not global. | n/a — not a deploy target |
| Hooks | Workspace-local **`.agents/hooks.json`** (global hooks via `~/.gemini/config/`). Different protocol from our shared scripts: agy hooks read stdin JSON and write `{"decision":"allow"\|"deny"}` on **stdout** (not exit-2). | supported, workspace-local |
| Statusline | **Native, always-on** TUI bar (no file to deploy) | ✅ native |

### agy's customization model (verified 2026-06-11)

agy has two **customization roots**: a Global root (`~/.gemini/`, with the agy-specific `~/.gemini/antigravity-cli/`) and a per-workspace root (`.agents/` in the repo). This is why agy's enforced-tier cells split the way they do in `dotfiles agent overview`'s Uniformity matrix:

- **rules** → `~/.gemini/AGENTS.md` (global). ✓ deployed.
- **skills** → `~/.gemini/antigravity-cli/skills/` (global, SKILL.md). ✓ deployed (33 linked). Workspace skills also load from `.agents/skills/`.
- **permissions** → `~/.gemini/settings.json` `tools.exclude`. ✓ deployed.
- **statusline** → native built-in; marked active via the agy config-root probe (nothing to deploy).
- **subagents** → `○` *by design*: dynamic/programmatic dispatch, no global `.md` dir. Do **not** plan to port `ai/subagents/*.md` here.
- **hooks** → `○`: closable only per-workspace (`.agents/hooks.json`) and in agy's JSON-decision protocol, not our global exit-2 scripts. A `--workspace` deploy was scoped and **declined** (narrow payoff + unverifiable agy runtime) — revisit if agy ships a global hook path or you live in agy-driven repos.

Sources: [transitioning blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) · [agy skills/MCP config](https://medium.com/google-cloud/configuring-mcp-servers-and-skills-for-antigravity-cli-and-ide-a938c7eebb78) · [agy hooks docs](https://antigravity.google/docs/hooks) · live binary/filesystem probe (2026-06-11, v1.0.7).

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
| **`fallbackModel`** (up to 3, tried in order on overload) + `--fallback-model` | Claude Code | **adopt** | free resilience — set a fallback (e.g. Sonnet) so an Opus overload doesn't stall. *Needs your fallback-model pick before wiring into settings.* |
| `disableBundledSkills` / `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | Claude Code | **evaluate** | hide vendor-bundled skills from the model — fits our aggressive skill curation. |
| `Stop`/`SubagentStop` hooks return `additionalContext` (feedback w/o erroring); hook-condition `$()`/`$VAR`/`$HOME` bugfix | Claude Code | **note** | the bugfix validates our deny-vocab guard approach; `additionalContext` is a future option for the guard hooks. |
| **2.6 "MCP Apps"** + CLI hooks (`beforeSubmitPrompt`/Pre/PostToolUse/stop) + nested subagents + `local.customTools` | Cursor | **note** | past 2.5; CLI hooks mean Cursor could satisfy the canonical hook intents natively if we ever script it headless. |
| **0.79.0** + **Project Trust** gating (`--approve`/`project_trust`); repo moved → `earendil-works/pi`; stale `./hooks` subpath removed (confirms no-hooks stance) | Pi | **note** | Project Trust aligns with our security posture; `Gondolin` (route built-in tools into a local micro-VM) is a sandboxed-exec adopt-candidate. |

Flagged **unverified, do NOT cite**: "Claude Fable 5 / Mythos-class" model (no Anthropic corroboration; appears in Pi's `[Unreleased]` too — noise until confirmed); Codex "native subagents/hooks/skills" (secondary sources only — don't flip matrix cells); Cursor "3.x" numbers (app builds, not a feature line past 2.6).

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

Hooks are **deterministic, harness-side automation** fired at lifecycle points. The key property: **they cost the model zero context** (they're shell commands the harness runs, not tokens the model reads), so unlike rules/MCP they aren't a budget concern — they're pure "make the floor deterministic."

**One shared script per intent, deployed verbatim.** The scripts live in `ai/agents/shared/hooks/` and are **payload-defensive** — each reads the path/command from whichever JSON key the harness uses (Claude/Codex `.tool_input.*` · Cursor `.filePath`/`.command`), so one script serves every vendor. Only the native *event name* differs. `dotfiles agent overview` renders the **Hooks matrix by intent** (proven by the shared script's basename in each vendor's config).

| Intent (shared script) | Claude | Codex | Cursor | agy | Pi |
|---|---|---|---|---|---|
| **guard-file** `guard-sensitive-file.sh` (block creds/keys/.env) | `PreToolUse` Edit\|Write | `PreToolUse` Edit\|Write | `preToolUse` Write\|Edit | ○ workspace-local | ○ ext |
| **guard-shell** `guard-destructive-shell.sh` (force-push, hard-reset, clean -f, rm -rf ~/, …) | `PreToolUse` Bash | `PreToolUse` (all) | `beforeShellExecution` | ○ | ○ `safe-git` |
| **format** `format-on-save.sh` | `PostToolUse` | `PostToolUse` | `afterFileEdit` | ○ | — |
| **notify** `notify.sh` (env-derived label) | `Stop` + `Notification` | `Stop` + `PermissionRequest` | `stop` | ○ | — |

All three file-based vendors (Claude/Codex/Cursor) carry the full intent set — the guards block via **exit 2** (Claude/Codex/Cursor share that convention). Two real safety gaps were closed in the consolidation: **Codex had no destructive-shell guard**, **Cursor had no credential-file guard**.

**The `○` cells are architectural, not pending:**
- **agy** registers hooks **workspace-local** (`.agents/hooks.json`) in a different protocol — stdin JSON → stdout `{"decision":"allow"|"deny"}`, *not* exit-2 — so our global shared scripts can't be dropped in. Not a global deploy target.
- **Pi** guards via the `safe-git` extension (its native mechanism), not our shared set.
- **Notify is the loosest** intent (quality-of-life, not a safety floor), so its absence on agy/pi is harmless.

**To change a hook:** edit the per-vendor script (`ai/agents/<vendor>/hooks/`); the intent set above is the contract each vendor must satisfy. New hard-stop guard patterns belong in `deny-commands.yaml` *first* (the config floor), then the guard hook is the runtime backstop.

---

## Adding a new agent to the fleet

1. Add a `setup_<vendor>()` module under `cli/src/dotfiles/cmd/agent/vendors/`.
2. Deploy rules (`build_global_instructions` → its instruction file), MCP (`mcp_servers_for`), subagents (`deploy_subagents` if it reads an agents dir), and a permission posture.
3. If it can express a deny list, add it as a surface in `deny-commands.yaml` + `deny_commands.py` (`SURFACES`, `SURFACE_FILES`, `deny_strings_in_config`), and hand-author the strings — the drift test will hold it in sync.
4. If it supports hooks, satisfy the canonical intent set (guard / format / notify) via its event names; map them in the [Hooks](#hooks--one-intent-set-three-events-per-vendor) table.
5. Add it to the [capability matrix](#capability-matrix-target-state) (and `capability_matrix.py` + the drift test) so its surfaces are tracked.
6. If it runs through Zed/ACP, remember the two-surface rule: its in-Zed approvals are governed by `editors/zed/settings.json`, not its own config.
