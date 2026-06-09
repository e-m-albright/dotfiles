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

**Status: staged, not yet executed** — `agy` is not installed on this machine and several config paths are unverified. Do **not** script the unverified surfaces until confirmed on a live `agy`.

Verified Antigravity facts (sources below):

| Surface | Config | Confidence |
|---|---|---|
| Install | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` → `~/.local/bin/agy` | verified |
| Global instructions | `~/.gemini/AGENTS.md` **and** `~/.gemini/GEMINI.md` (GEMINI.md outranks AGENTS.md). **GEMINI.md is not dead.** Prefer **AGENTS.md** for portability — both `agy` and Gemini CLI hard-code `~/.gemini/GEMINI.md`, so running both leaks rules (gemini-cli #16058, closed "not planned"). | verified |
| Skills | global `~/.gemini/antigravity-cli/skills/<name>/SKILL.md`; project `.agents/skills/` | verified |
| MCP | `mcp_config.json` (global `~/.gemini/antigravity-cli/`); remote uses `serverUrl` (renamed from `url`) | partial |
| Plugins | `agy plugin` CLI; `agy plugin import gemini` to migrate Extensions | verified |
| Subagents · Hooks · Permissions · Statusline | **paths/format unverified** — confirm on a live `agy` first | ⚠️ |

**Migration plan when `agy` lands:** (1) install `agy`; (2) `agy --version` + inspect `~/.gemini/` and `~/.gemini/antigravity-cli/` to verify the unverified paths; (3) replace the `gemini` vendor in `dotfiles.agent.VENDORS` with `antigravity` (display "Antigravity"); (4) write `vendors/antigravity.py` deploying the kernel to `~/.gemini/AGENTS.md`, MCP→`mcp_config.json`, skills via the shared pipeline, and — once verified — subagents/hooks/permissions; (5) flip the matrix column gemini→antigravity and close its now-supported skills/subagents/hooks. The `dotfiles agent web copy` Gemini-web-chat command is unrelated (it pastes prompts into the Gemini *web* app) and stays.

Sources: [transitioning blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) · [Antigravity subagents/skills](https://developers.googleblog.com/subagents-have-arrived-in-gemini-cli/) · Gemini CLI v0.26.0 (Skills/Hooks/Subagents) · gemini-cli issue #16058.

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

## Adding a new agent to the fleet

1. Add a `setup_<vendor>()` module under `cli/src/dotfiles/cmd/agent/vendors/`.
2. Deploy rules (`build_global_instructions`), MCP (`mcp_servers_for`), and a permission posture.
3. If it can express a deny list, add it as a surface in `deny-commands.yaml` + `deny_commands.py` (`SURFACES`, `SURFACE_FILES`, `deny_strings_in_config`), and hand-author the strings — the drift test will hold it in sync.
4. If it runs through Zed/ACP, remember the two-surface rule: its in-Zed approvals are governed by `editors/zed/settings.json`, not its own config.
