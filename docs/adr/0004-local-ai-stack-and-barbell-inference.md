# Local-AI stack: Zed default editor, LM Studio local models, barbell inference

**Date**: 2026-05-25.
**Status**: accepted.

## Context

[ADR-0003](0003-vendor-locked-clis-over-aggregators.md) settled the *frontier* coding-agent question (Claude Code + Codex + Cursor on subscriptions). This ADR settles the complementary *local / self-hosted* axis, explored on a 48GB M4 Pro in May 2026.

Findings that shaped the decision:

- **The open-weights frontier is not locally runnable.** The best open coders (Kimi K2.6, DeepSeek V4 Pro) are 1T+ param MoEs — they need a datacenter, not a laptop. Locally runnable models (Gemma 4 e4b/26B/31B, Qwen3-Coder-30B-A3B) are "good junior" tier: fine for routine prose/notes and light edits, not a Claude Code replacement.
- **Anthropic banned third-party OAuth** (2026-02-20, enforced ~Apr 4). Subsidized Claude inference is now locked to the first-party Claude Code binary — reinforcing ADR-0003 and killing any "bridge my Max sub through a universal CLI" plan.
- **Paid OSS-inference hosts** (Together, Fireworks, DeepInfra, Groq, Cerebras, Parasail, Baseten, CoreWeave, Clarifai, …) are a crowded, capable middle tier — but they fit neither end of our actual usage.
- **Terminal agents** (opencode, crush, pi, goose) are good but feel too heavy for a daily driver versus a real IDE.
- **Zed shipped 1.0** (2026-04-29) with **ACP (Agent Client Protocol)** — it can host external agents (Claude Code, Codex, Gemini CLI) inside the editor, so "one window" no longer means "give up the frontier agent."

## Decision

**Adopt a barbell inference strategy and a ~3-tool workflow.**

- **Inference is a barbell, skip the middle.** Either local/self-hosted (full privacy, ~$0 marginal cost) **or** frontier via subsidized subscription (Claude Max / OpenAI). Paid OSS-inference hosts have no niche for us — they only win on high-volume parallel automation, no-rate-limit needs, or models too big to run locally but cheaper than frontier, none of which is our profile.
- **Default editor: Zed.** Set as `$EDITOR` / git editor and the `.md`/`.txt` open handler (`shell/.zshrc`, `git/.gitconfig`, `macos/file-associations.sh`). Faster boot than Cursor; ACP can host Claude Code/Codex so the IDE can be the single surface. Cursor stays installed as the AI-native IDE.
- **Local runner: LM Studio.** MLX-native (faster than Ollama on Apple Silicon), model browser, OpenAI-compatible server at `localhost:1234/v1`. Config logged in `macos/lmstudio.sh` (`LMSTUDIO_MODEL=google/gemma-4-e4b`, `LMSTUDIO_CONTEXT=32768`) and wired into `install.sh`. Ollama stays disabled (LM Studio covers it; re-enable for CLI runners). Jan / Msty are honorable mentions.
- **~3-tool workflow:** Zed (+ local Gemma or an efficient frontier-OSS model) for low–medium complexity and direct code editing; **Claude Code / Codex CLI** for high-complexity work.

## Why

- **The barbell is honest about where value is.** Local is free and private; frontier subscriptions are wildly subsidized (Max 20× measured at ~$1,400/mo of API-equivalent value for $200). Paying a metered host for a mid-tier open model captures neither advantage.
- **Local context gotcha is real and now handled.** LM Studio loads at a 4096-token window by default — too small for agent system prompts (Zed's agent alone is ~10.5K tokens of prompt + tool schemas). Pinning the context in `macos/lmstudio.sh` removes the foot-gun.
- **ACP collapses the tool count.** Zed hosting Claude Code means the editor we already prefer can also be the frontier-agent surface — fewer windows, same power.
- **Small local models are "good junior," not peer.** Setting that expectation prevents wasting the local tier on tasks it will fail (multi-file agentic refactors) and aims it at what it's good for (notes, prose, small edits).

## Trade-offs accepted

- **No local frontier.** Until open weights match Sonnet/Opus *and* shrink enough to run on the laptop, the high end stays subscription-only.
- **LM Studio context persistence.** `lms load -c` is runtime; the per-model default must also be set once in the LM Studio app so JIT reloads don't revert to 4096. Documented in-script.
- **Two editors.** Zed (default/quick) + Cursor (AI-native IDE) — accepted; they serve different moments.

## Revisit if

- An open-weights model matches frontier coding *and* runs in ~48GB (then the barbell's local end moves up and the high-complexity tier may shift local).
- LM Studio / MLX stops being the best Mac runner, or Ollama's Mac story overtakes it.
- A paid OSS-inference need actually materializes (sustained parallel automation, no-rate-limit batch, or a too-big-for-laptop model that's cheaper than frontier).
- Zed's ACP hosting of Claude Code becomes good enough to drop the standalone Claude Code CLI from daily use.

## See also

- [ADR-0003](0003-vendor-locked-clis-over-aggregators.md) — frontier CLI / subscription decision this builds on
- `docs/tools-to-evaluate.md` — personal stack rankings (self-hosted / paid-infra / closed / harnesses)
- `macos/lmstudio.sh` — local model + context config (source of truth for the chosen model/window)
- `prompts/guides/ai-tools.md`, `prompts/guides/ai-coding-frameworks.md` — landscape notes
