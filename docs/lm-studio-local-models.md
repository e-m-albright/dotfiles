# LM Studio Local Model Notes

Last updated: 2026-05-25

## Local hardware baseline

Current machine:

- MacBook Pro `Mac16,7`
- Apple M4 Pro
- 14-core CPU: 10 performance + 4 efficiency
- 20-core GPU
- 48 GB unified memory
- Metal 4

This is strong enough for useful local 20B-35B quantized models, but speed-sensitive agent loops should prefer smaller active/effective models.

## Current default

Use **Gemma 4 E4B** for now.

Reason: speed is the priority. Gemma 4 E4B should feel substantially snappier than larger MoE/dense options while still supporting image input, reasoning, and tool calling.

Dotfiles config:

- Pi default: `agents/pi/settings.json`
- LM Studio provider/model registry: `agents/pi/models.json`
- Deployed to: `~/.pi/agent/settings.json` and `~/.pi/agent/models.json`

Current Pi default:

```json
{
  "defaultProvider": "lm-studio",
  "defaultModel": "google/gemma-4-e4b"
}
```

## Models evaluated

Dates are approximate from the LM Studio listing age observed on 2026-05-25.

| Model | Approx listed date | Notes | Local fit on M4 Pro / 48 GB |
|---|---:|---|---|
| Nemotron 3 Nano Omni | 2026-04-28 | Multimodal image/text model for Q&A, summarization, document intelligence | Consider for local document/vision workflows |
| Qwen3.6 27B | 2026-04-22 | Dense 27B; coding/productivity-oriented | Capable but likely slower than MoE/smaller options |
| Qwen3.6 35B A3B | 2026-04-17 | MoE-ish active 3B; stability + coding utility focus | Best theoretical coding/capability balance, but not chosen now because speed is priority |
| Gemma 4 31B | 2026-04-11 | Dense 31B; vision, reasoning, tool calls | Capable but likely heavier/slower |
| Gemma 4 E4B | 2026-04-11 | Effective 4B; image input, reasoning, tool calls | **Chosen default: best speed/capability balance for daily local use** |
| Gemma 4 E2B | 2026-04-11 | Effective 2B; image input, reasoning, tool calls | Fastest fallback, lower capability |
| Gemma 4 26B A4B | 2026-04-02 | 26B total / active 4B MoE; vision + reasoning | Better quality ceiling than E4B, but slower and more memory-bandwidth heavy |
| Nemotron 3 Nano 4B | 2026-03-16 | General reasoning/chat | Lightweight fallback |
| Qwen3.5 9B | 2026-03-03 | Dense 9B; 262k native context | Good fast long-context fallback |
| Qwen3.5 35B A3B | Unknown from snippet | Reasoning vision-language model | Needs separate evaluation |

## Speed: Gemma 4 E4B vs Gemma 4 26B A4B

Expected local feel at similar quantization:

- **Gemma 4 E4B**: very fast, low memory pressure, good for interactive local assistant and tight agent loops.
- **Gemma 4 26B A4B**: higher quality ceiling, but total 26B weights still create more memory bandwidth and prompt-processing cost even if active compute is around 4B.

Rule of thumb on this machine:

- Gemma 4 E4B should usually feel **~1.5x-3x faster** than Gemma 4 26B A4B, depending on quantization, context length, LM Studio backend, and whether vision/tool calling is involved.

Use 26B A4B only when the E4B result is clearly not good enough.

## Why not Qwen3.6 35B A3B as default yet?

Qwen3.6 35B A3B remains the best-looking candidate for coding/agent capability because the listing emphasizes stability, real-world utility, responsiveness, and productive coding.

However, current priority is **local speed**. For fast loops, Gemma 4 E4B is the safer default:

- lower memory footprint
- faster prompt ingestion
- faster generation
- less system pressure while browsers/editors/agents are also running
- multimodal support remains available

Keep Qwen3.6 35B A3B on the shortlist for a higher-capability local coding model once we want to trade speed for quality.

## Recommended operating pattern

- Default daily local model: **Gemma 4 E4B**
- Escalate for harder coding/reasoning: **Qwen3.6 35B A3B**
- Escalate within Gemma family: **Gemma 4 26B A4B**
- Long-context fallback: **Qwen3.5 9B**
- Multimodal document workflows: **Nemotron 3 Nano Omni** or Gemma vision-capable variants
