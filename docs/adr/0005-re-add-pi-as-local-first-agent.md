# Re-add Pi as a managed local-first terminal agent (narrow scope)

**Date**: 2026-05-25.
**Status**: accepted. Amends [ADR-0003](0003-vendor-locked-clis-over-aggregators.md).

## Context

[ADR-0003](0003-vendor-locked-clis-over-aggregators.md) dropped Pi (and opencode / gemini-cli / kimi-cli) because the value proposition being evaluated was *"bridge a frontier subscription through a vendor-neutral CLI"* — which is bad economics (subscriptions are subsidized only in first-party clients) and ToS-gray (Anthropic's OAuth ban, confirmed Feb 2026).

Two things changed since:

- [ADR-0004](0004-local-ai-stack-and-barbell-inference.md) established the **barbell**: local/self-hosted on one end, subsidized frontier subscriptions on the other.
- Hands-on, **Pi is genuinely excellent as a lightweight, local-first terminal agent** — ~1k-token system prompt, 4 tools, hackable, mid-session provider swap, and headless modes (`pi -p`, `--mode rpc`, SDK).

The economic objection in ADR-0003 **does not apply to Pi running local LM Studio (free) or a BYO key** — we are not using Pi to bridge a subsidized subscription. Confirmed: Anthropic in Pi is pay-per-token / ToS-gray, so Pi is explicitly *not* our Anthropic-Max path (that stays Claude Code / Zed-ACP).

## Decision

**Re-add Pi as a managed agent (`agents/pi/`), scoped to local-first + lightweight-terminal + headless-automation use** — not subscription bridging.

- `agents/pi/setup.sh` added to `dotfiles agent setup` (4th target after claude/cursor/codex).
- Deploys: `settings.json` (default → **local LM Studio / gemma-4-e4b**, not Anthropic), `models.json` (LM Studio provider), `~/.pi/agent/AGENTS.md` (baked rules, same source as Codex), subagents (`~/.pi/agent/agents/*.md`).
- **Skills are shared, not duplicated** — Pi reads `~/.agents/skills/`, the same directory Codex's `npx skills` deploy populates. Zero per-tool skill copies.
- Installs **`pi-superpowers-plus`** (third-party Superpowers port: TDD/verification gating + subagents) — runs with full permissions; opt-out by commenting the block.
- Automation: Pi headless (`pi -p`) + our own cron/CI is the vendor-agnostic scheduling path (Zed has none).

## Why

- **Different use case than ADR-0003 rejected.** That ADR killed Pi-as-subscription-aggregator; this adds Pi-as-local-first-terminal-agent. Both can be true.
- **Marginal config cost ≈ zero.** AGENTS.md and `.ai/skills/` are already portable (Pi reads `~/.agents/skills/`); subagents map to `~/.pi/agent/agents/*.md`. We write once, deploy everywhere.
- **Fills a niche Zed can't.** Terminal-native, scriptable/headless (`pi -p`/SDK), and the agnostic-automation engine. Zed is the editor surface; Pi is the lightweight/headless surface.

## Trade-offs accepted

- **A 4th managed tool.** Mitigated by shared skills/AGENTS.md — the per-tool surface is small (settings + models + a setup script).
- **`settings.json` git churn** — Pi auto-writes `lastChangelogVersion`; the symlinked tracked file will see periodic noise.
- **Third-party `pi-superpowers-plus`** runs arbitrary code with full permissions. Accepted as an explicit opt-in; pinned to one package, reviewable.
- **Default model changed** from the user's prior `anthropic/claude-opus-4-7` (pay-per-use API in Pi) to local `lm-studio/google/gemma-4-e4b` (free). Switch any time via `/model`.

## Revisit if

- Pi falls out of daily use (then drop `agents/pi/` and the setup-target again).
- Maintenance burden exceeds value, or `pi-superpowers-plus` proves untrustworthy.
- A sanctioned subscription path opens that changes the calculus (unlikely to affect the *local* rationale).

## See also

- [ADR-0003](0003-vendor-locked-clis-over-aggregators.md) — the decision this narrows
- [ADR-0004](0004-local-ai-stack-and-barbell-inference.md) — barbell inference + Zed/LM Studio
- `docs/tools-to-evaluate.md` — "AI Tooling Research Notes (2026-05)": subscription landscape, harness benchmarking, automation portability
- `agents/pi/setup.sh`, `agents/pi/models.json` — the implementation
