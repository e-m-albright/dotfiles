# Local LLM Stack

**Decision (2026-05-28):** LM Studio only. Ollama and llama.cpp evaluated and dropped.

## Hardware

M4 Pro, 48 GB unified memory. Plenty of room for 7B–30B models with comfortable
context windows.

## Runtimes Evaluated

| Runtime | Backend(s) | Distribution | Status |
|---|---|---|---|
| **LM Studio** | MLX (Apple-native), bundled llama.cpp | GUI + `lms` CLI + OpenAI-compatible server on :1234 | **Kept** |
| Ollama | Custom runner wrapping llama.cpp/ggml | CLI + server on :11434, model registry | Dropped |
| llama.cpp | Metal | `llama-cli`, `llama-server`, `llama-bench` via Homebrew | Dropped |

## Benchmark — Llama-3.2-1B-Instruct (M4 Pro, identical model family)

Methodology: `pp128` (prompt-eval phase) measured via TTFT on a 128-token prompt
with `max_tokens=1`; `tg128` (token-gen phase) measured via LM Studio's
`/api/v0/chat/completions` `stats.tokens_per_second` (gen-only, post-TTFT) or
llama.cpp's `llama-bench -p 128 -n 128`.

| Backend | Quant | **tg tok/s** | pp tok/s |
|---|---|---:|---:|
| LM Studio — MLX | 4-bit | **278** | 1,291 |
| llama.cpp (brew) — Metal | Q4_K_M | 207 | 2,827 |
| LM Studio — bundled llama.cpp | Q8_0¹ | 156 | 2,562 |
| Ollama — Metal | Q4_K_M | 131 | — |

¹ Default `lms get` quant was Q8_0, not Q4_K_M. Heavier quant explains lower
tg than raw llama.cpp Q4_K_M; pp similar since both use llama.cpp.

### Loaded-model spot-check (Qwen3.6-27B, MLX)

- pp: 85.7 tok/s
- tg: 12.3 tok/s
- TTFT: 1.06 s on short prompt

## Findings

- **MLX wins token generation by ~34%** over raw Metal llama.cpp on Apple
  Silicon for the same model. This is the metric that matters most for chat
  UX (output speed).
- **llama.cpp wins prompt eval throughput by ~2.2×.** Matters for long-context
  / RAG workloads where the prompt dominates total wall time.
- **Ollama is dominated** on both axes. Its value prop (model registry,
  de-facto `:11434` API target) does not offset the perf tax for personal use,
  and LM Studio's `:1234` is OpenAI-compatible — any app that "wants Ollama"
  can be pointed at LM Studio in one config line.

## Decision

Run **LM Studio only**. Default to MLX quants when available; fall back to
GGUF when MLX isn't published yet.

### When to reconsider

- **Long-context RAG becomes a hot path:** revisit `llama.cpp` for its
  pp throughput advantage. `brew install llama.cpp` and run
  `llama-server -hf <repo>:<quant>`.
- **A new model lands on Hugging Face before LM Studio packages it:**
  same — `brew install llama.cpp`, use `-hf` shorthand.
- **An app integration is hardcoded to Ollama's `:11434` API and can't be
  reconfigured:** reinstall Ollama OR run LM Studio on a port alias. The
  former is simpler, the latter avoids the perf tax.

## Re-running the benchmark

The methodology is preserved in this doc. Quick reproduction:

```bash
# LM Studio (model must be loaded first via `lms load`):
curl -s http://localhost:1234/api/v0/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"<id>","messages":[{"role":"user","content":"Count to 200."}],
       "max_tokens":128,"temperature":0}' \
  | jq '.stats'

# llama.cpp (requires `brew install llama.cpp`):
llama-bench -hf <repo>:<quant> -p 128 -n 128
```

LM Studio's `stats.tokens_per_second` is post-TTFT and maps directly to
llama-bench's `tg` number.
