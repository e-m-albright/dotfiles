# Local LLM Stack — M4 Pro 48GB

**Decision (2026-05-29):** LM Studio only, MLX-preferred. Ollama and llama.cpp
evaluated and dropped. Two models kept: Qwen3.6-35B-A3B (coding/agents) and
Gemma-4-E4B (vision/quick chat).

The managed model and context settings live in `macos/lmstudio.sh`. Agent-specific
model routing belongs to Workbench, not this host repository.

## Hardware envelope

- **M4 Pro, 48 GB unified memory**
- Metal `recommendedMaxWorkingSetSize` reported by llama.cpp init: **40.2 GB**
  — practical GPU memory ceiling. Past this you start fighting macOS for RAM.
- Inference on Apple Silicon is **memory-bandwidth-bound, not compute-bound**.
  Mid-sized GGUF models hit a soft ceiling around **55 tok/s** regardless of
  active param count — a 7.5B dense and a 35B-with-3B-active MoE both come in
  there. MLX bypasses some of this and gets to ~77 tok/s on the same models.

## What runs well

| Model | Params (active) | Quant | Size | tok/s | Best for |
|---|---|---|---:|---:|---|
| Qwen3.6-35B-A3B | 35B / 3B MoE | MLX 4-bit | 20.4 GB | **77** | Coding, agents, daily driver |
| Gemma-4-E4B-it | 7.5B dense | MLX 4-bit | 6.9 GB | ~70 | Vision, multimodal, quick chat |

## What does NOT run well (tested + rejected)

| Model | Why rejected |
|---|---|
| Qwen3.6-27B (dense, MLX) | **14 tok/s** — 5.4× slower than 35B-A3B. Memory-bandwidth bound; dense 27B reads ~17 GB/token from RAM. Quality is ~3-4 SWE-Bench points better, but UX cost too high. |
| Qwen3.6-27B (dense, GGUF) | 12 tok/s — even worse. |
| Qwen3.6-35B-A3B (GGUF) | 56 tok/s — MLX variant strictly dominates (+36%, less memory). |
| Ollama runtime | ~30% slower than raw llama.cpp on same model. Redundant with LM Studio. |

## Performance — Llama-3.2-1B sanity bench (cross-runtime)

This is the cheapest cross-runtime comparison because the model is tiny enough
that the runtime overhead dominates.

| Runtime | Quant | tg tok/s | pp tok/s |
|---|---|---:|---:|
| LM Studio MLX | 4-bit | **278** | 1,291 |
| llama.cpp (brew, raw) | Q4_K_M | 207 | 2,827 |
| LM Studio bundled llama.cpp | Q8_0 | 156 | 2,562 |
| Ollama Metal | Q4_K_M | 131 | — |

**Read this as:** MLX wins token gen by 30-80%; llama.cpp wins prompt-eval by
2-3× (matters only for huge prompts / RAG).

## Context window economics

Three things govern how big a context you can load:

### 1. KV cache cost per token (varies by architecture)

| Architecture | KV cache | 256K context |
|---|---:|---:|
| Dense 27B (multi-head attention) | ~123 KB/token | +30 GB (won't fit) |
| MoE 35B-A3B (Grouped Query Attention) | ~33 KB/token | +8 GB ✅ |
| Gemma-4 (sliding window + global hybrid) | **~constant** (cap on window) | ~0 extra ✅✅ |

Gemma's sliding-window attention means context cost is bounded — `lms` reports
identical memory at 32K, 128K, 256K, 512K (all ~9 GB). Don't be afraid to set
it big.

### 2. Metal working set ceiling

40.2 GB on this machine. Model weights + KV cache must fit underneath this. For
the 35B-A3B MoE: 20.4 GB weights + 8 GB KV at 256K = 28 GB → fits comfortably.

### 3. LM Studio guardrails

LM Studio's "resource guardrails" warn / refuse to load above a configured
threshold. The warnings are *conservative* — you can usually load past them.
GUI: Settings → Hardware → Resource Guardrails → "Relaxed" or "Off" if needed.

## Quality benchmarks for local coding models (May 2026)

| Model | SWE-Bench Verified | Terminal-Bench 2.0 | LiveCodeBench Coding |
|---|---:|---:|---:|
| Qwen3.6-27B (dense) | **77.2%** | **59.3%** | 71.8 |
| Qwen3.6-35B-A3B (MoE) | 73.4% | 51.5% | ~mid-60s |
| Gemma-4-E4B | (not coding-tuned) | — | — |

**Quality vs speed tradeoff is real.** 27B wins on every benchmark by 3-11
points, but is 5.4× slower. For interactive agentic work, 35B-A3B wins on UX;
for offline / batch quality runs, the 27B is worth re-pulling.

## Gotchas

### JIT-load default context = 4096

If you `lms load` a model and let it expire (TTL), or call the API without
a model pre-loaded, LM Studio JIT-loads at the engine's default **4096**
context regardless of what the model supports. This causes `tokens to keep >
context length` errors from any agent (Zed, Pi) sending a real-sized prompt.

**Fix:** load with explicit `-c <ctx>` and a long `--ttl`:

```bash
lms load qwen3.6-35b-a3b -c 262144 --ttl 86400 -y
```

Or set it permanently in GUI: My Models → gear → Context Length → Save default.

### Thinking-mode tax

Qwen3.6 family models silently emit 200-2500+ `reasoning_tokens` before any
visible output. Budget **3-5× your visible token target** in `max_tokens` or
the model gets cut off mid-think.

LM Studio's `enable_thinking: false` via `chat_template_kwargs` was not
honored on this build (May 2026) — if it bothers you, try updating the runtime
in Discover → Runtimes, or set it in the GUI's per-model load settings.

### Model ID changes after dependency cleanup

`lms ls` shows different IDs depending on whether a hub manifest exists. When
you delete a GGUF and only the MLX remains, the ID may drop the `mlx-community/`
prefix and just become e.g. `qwen3.6-35b-a3b`. Update Pi/Zed configs accordingly.

### `lms get` can't always pull MLX-community models

`lms get mlx-community/<name>-4bit -y` often fails with "artifact does not
exist". Workaround: use the full HF URL:

```bash
lms get "https://huggingface.co/mlx-community/<name>-4bit" -y
```

## Decision framework for evaluating a new model

When considering a new local model:

1. **Architecture check:** is it MoE? Look for `A<N>B` in the name (e.g. 35B-A3B
   = 35B total, 3B active). MoE-with-small-active is the only way to run
   large-feeling models at usable speed on this hardware.
2. **MLX availability:** check `mlx-community/<name>` on HF. If yes, prefer it
   over GGUF. If no, GGUF works but expect 25-40% less throughput.
3. **Size budget:** model on disk should be < 25 GB to leave room for KV cache
   + macOS. At Q4: keep total params under ~50B dense or ~80B MoE.
4. **Context KV math:** estimate at target context via `lms load -c <ctx>
   --estimate-only -y`. Must stay under 40 GB Metal working set.
5. **Benchmark check:** look up the model on the [Aider Polyglot
   leaderboard](https://aider.chat/docs/leaderboards/), SWE-Bench Verified,
   and Terminal-Bench 2.0. For coding work, Terminal-Bench is the most
   predictive of real agentic behavior.
6. **Speed check:** use LM Studio's current runtime metrics during a representative
   prompt. Target: > 40 tok/s generation for interactive use and > 100 for
   autocomplete.

## Process learnings (this session)

- **Verify model SKUs before recommending.** I claimed "Qwen3-Coder-14B" existed
  — it doesn't (Qwen3-Coder family is only 30B-A3B, 480B-A35B, and Coder-Next).
  Always cross-check HF before naming a model.
- **Flag capability loss when deleting.** When asked to delete "the GGUF
  models", I deleted Gemma without flagging it was the only vision-capable
  model on disk. Surface that first.
- **GUI vs CLI defaults diverge.** LM Studio's CLI-loaded context doesn't
  persist as a model default — only GUI "Save as default" does. Document the
  one-time GUI step rather than expect CLI flags to stick.
