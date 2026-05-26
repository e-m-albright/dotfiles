# Use vendor-locked CLIs (Claude Code, Codex, Cursor) over aggregators

**Date**: 2026-05-12.
**Status**: accepted.

## Context

Over 2026-05-07 → 2026-05-12 we explored consolidating to a single vendor-neutral coding-agent CLI. The candidates investigated were:

- **opencode** (sst, MIT) — provider-agnostic, mature, brew-distributed
- **Pi / oh-my-pi** (`omp`, can1357) — opinionated harness, hash-anchored edits
- **gemini-cli** (Google), **kimi-cli** (Moonshot) — vendor-locked alternatives

All four were installed, fully wired into `dotfiles agent setup` (skills + subagents + MCP + global instructions + rule baking), and verified via `dotfiles verify vendors`.

While exploring "use my Claude subscription through opencode," three structural facts surfaced:

### 1. Subscription economics dominate for heavy users

Provider pricing comparison (rough, late-2026):

| Plan | $/month | Equivalent API token spend for power user |
|------|---------|---|
| Claude Max 20× | $200 | $600–$1500/mo (Sonnet 4.5: $3/$15 per M in/out) |
| ChatGPT Pro | $200 | similar order of magnitude |
| Cursor Ultra | $200 | similar |
| OpenRouter (BYO) | metered, no markup on tokens, 5.5% credit fee | strictly equal-to-API |

Every major lab subsidizes heavy users on flat-rate plans. Crossover from API-cheaper to subscription-cheaper sits around 4–8 hours/week of active agent use — well below our actual usage.

### 2. Subscriptions are bound to the official client

- **Anthropic** explicitly scoped Pro/Max OAuth tokens to Claude Code in late 2025 and tightened enforcement against third-party harnesses. Community workarounds (Meridian, opencode-claude-auth) are ToS-gray and fragile by design — Anthropic has shown willingness to break them.
- **OpenAI** is more tolerant; the Codex OAuth flow can be used through opencode plugins, but commercial use is disclaimed.
- **Cursor** is closed entirely — no API surface for third parties to consume the subscription.

### 3. The "one CLI" trilemma

You cannot have all three of:

1. Single CLI
2. Best-designed agentic tool
3. Subscription pricing benefit

Pick any two:

| Combination | What you get | What you give up |
|---|---|---|
| Single + best + API | opencode + BYO key | 3–10× cost at scale |
| Single + subscription + locked | Claude Code on Max **or** Codex on Pro | provider choice |
| Multi-CLI + best + subscription | Claude Code + Codex CLI + Cursor side-by-side | one-CLI ergonomics |

## Decision

**Adopt the multi-CLI + subscription combination.** Primary drivers:

- **Claude Code on Max 20×** — primary coding agent. Subscription is wildly subsidized vs equivalent API token spend at our usage; harness is best-in-class today (subagents, skills, hooks, MCP-native, plan mode).
- **Codex CLI on ChatGPT Plus** — secondary, for GPT-5 second opinions and non-Claude workflows.
- **Cursor (subscription)** — editor + agent in a single IDE for Cursor-specific UX.

**Roll back the aggregator track:**

- Uninstall: `opencode`, `oh-my-pi` (`omp`), `gemini-cli`, `kimi-cli` (machine cleanup).
- Delete: `agents/{opencode,pi,gemini,kimi}/` from this repo.
- Drop these targets from `agents/shared/mcp-servers.json`.
- Simplify `dotfiles agent setup` to invoke only `agents/{claude,cursor,codex}/setup.sh`.
- Simplify `dotfiles verify vendors` to probe only the three keepers.

**Keep everything that's vendor-neutral and reusable:**

- All ported skills (`diagnose`, `grill-with-docs`, `tdd-vertical-slices`, `improve-codebase-architecture`, `prototype`, `skill-creator`, `code-quality-audit` w/ U11) — they work in any harness.
- All ported subagents (`security-auditor`, `performance-engineer`, `debugger`, `error-detective`, `legacy-modernizer`, `shellcheck-reviewer`) — deployed to Claude Code + Codex.
- `agents/shared/bake-rules.sh` — used by Codex's AGENTS.md baking. Claude Code reads `~/.claude/rules/*.md` natively.
- `agents/shared/validate-skills.sh`, `agents/shared/verify-vendors.sh` — diagnostic tooling.
- `agents/claude/hooks/git-guardrails.sh` — PreToolUse safety hook.
- `bin/dotfiles agent setup` / `verify vendors` / `verify skills` — namespaced CLI restructure.
- `docs/skills-sources.md` — upstream attribution registry.
- Project-level scaffold integration (`.cursor/rules/`, `.gemini/rules/`, `.github/instructions/`) via `scaffold.sh` — unrelated to user-level CLI installs; stays as a per-project mechanism.

## Why

- **Money math is unambiguous.** At our usage level, Max + Plus is ~$220/mo all-in vs $600–$1500/mo API equivalent through opencode. The aggregator track is paying a 3–5× tax for provider neutrality we don't actually need yet.
- **Best-in-class harness is in Claude Code.** Subagents, skills, hooks, MCP, plan mode, TypeScript SDK — opencode is closing the gap but Claude Code is still the reference implementation.
- **ToS exposure isn't worth it.** Bridging Claude subscription into opencode via Meridian or token replay risks revocation; not safe to build a workflow around.
- **Vendor neutrality has a price.** OpenRouter (5.5% credit fee, no token markup) is the clean BYOK aggregator, but it's strictly pay-per-token — no subscription leverage. Useful for multi-model evals and bursty workloads; not a daily driver.
- **Optionality vs. cost.** Buying optionality at 3–5× the daily cost is expensive insurance against an event ("Anthropic does something annoying," "open models flatten the field") that may not happen. If it does, switching is a week of work, not a lifetime lock-in.

## Trade-offs accepted

- **Three tools, three UXes, three context windows.** Mitigated by unified rules/skills/MCP deployment via `dotfiles agent setup` — the surfaces under Claude Code / Codex / Cursor stay coherent even if the harnesses differ.
- **Provider lock-in fragility.** If Anthropic does something egregious, we're exposed. Acceptable risk; switch cost is bounded.
- **No self-hosted-model story yet.** When that becomes relevant (Kimi K3, DeepSeek V4, etc.), revisit — but the trigger is "open models match frontier for our workflow," not "vendor neutrality on principle."

## Revisit if

- Anthropic kills or severely caps the Max plan.
- Open-weight coding models match Sonnet/Opus on our specific workflow.
- A new aggregator emerges with sanctioned subscription access (not OAuth bridging).
- We genuinely need multi-model parallel evaluation as a core workflow (not occasional).

## See also

- [ADR-0001](0001-canonical-skills-symlinked-into-vendors.md), [ADR-0002](0002-canonical-skills-deploy-via-npx-skills.md) — earlier infrastructure decisions
- `docs/specs/2026-05-07-skills-research.md` (local notes) — the full exploration that fed this decision
- `docs/agent-model-routing.md` — per-agent model tier policy (Opus/Sonnet/Haiku)
