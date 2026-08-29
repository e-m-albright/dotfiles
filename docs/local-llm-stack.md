# Local LLM Stack — M4 Pro 48GB

> **Active for supervised private work; not trusted for autonomous operations.**
>
> oMLX is installed as the active open-source, MLX-native runner. An optimized
> Qwen3.6-35B-A3B build is the local default and also classifies Pi's automatic
> route. Model serving, tool calls, strict structured output, software-offline
> inference, and fail-closed local-provider failure have passed. A physical
> network-disconnect test and broader operational accuracy remain open.
>
> The measurements below preserve the original LM Studio evaluation where they
> still describe this hardware. Re-run them through oMLX before treating the old
> speeds as current. The cross-platform model, runtime, router, managed-host, and
> serverless-GPU ranking lives in Workbench's
> [open-model-inference.md](https://github.com/e-m-albright/workbench/blob/main/playbook/knowledge/open-model-inference.md).

**Current decision:** oMLX first, LM Studio as the fallback, and native MLX
weights. Qwen3.6-35B-A3B oQ4e with multi-token prediction is the private agent
and classifier. Gemma 4 26B-A4B was slower and showed no quality advantage in
the initial A/B, so its local weights were removed.

Agent-specific model routing belongs to Workbench. This host page owns the
runner, hardware envelope, measured performance, and privacy acceptance test.

## Reproducible installation

`macos/packages.toml` declares oMLX and its `omlx_setup` special installer.
`macos/configure-omlx.sh` idempotently installs and verifies xgrammar, repairs the
known macOS loader defect, merges the non-secret settings overlay from
`macos/omlx/settings.json`, downloads the selected Qwen weights when absent, and
restarts the service only after a change. Generated authentication material and
unknown future settings are preserved. Workbench owns Pi's provider, model,
router, and launcher configuration.

Run the full reconciliation with:

```bash
dotfiles brew install
```

## Structured output support

The managed setup installs oMLX with xgrammar so JSON schemas and tool arguments
can be enforced. The underlying Homebrew command is:

```bash
brew reinstall jundot/omlx/omlx --with-grammar
```

oMLX 0.6.3 may install the macOS binding without the loader metadata its own
formula expects. Verify after every reinstall:

```bash
"$(brew --prefix omlx)/libexec/bin/python" -c 'import xgrammar; print("xgrammar import OK")'
```

If that import cannot find `libxgrammar_bindings.dylib`, apply the formula's
loader fix manually:

```bash
site="$(brew --prefix omlx)/libexec/lib/python3.11/site-packages"
dylib="$site/xgrammar/libxgrammar_bindings.dylib"
record="$(find "$site" -maxdepth 1 -type d -name 'xgrammar-*.dist-info' -print -quit)/RECORD"
install_name_tool -add_rpath "$site/tvm_ffi/lib" "$dylib"
codesign --force --sign - "$dylib"
printf 'xgrammar/libxgrammar_bindings.dylib,,\n' > "$record"
"$(brew --prefix omlx)/libexec/bin/python" -c 'import xgrammar; print("xgrammar import OK")'
```

Remove this workaround when the upstream oMLX packaging fix supersedes it.

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
| Gemma 4 26B-A4B (MLX) | 65 tok/s versus Qwen's 71 in the local short-context A/B, with lower broad intelligence and no observed quality advantage. |
| Ollama runtime | ~30% slower than raw llama.cpp on same model. Redundant with LM Studio. |
| Qwen3.8-27B dense 4-bit | 14.3 tok/s conventionally and 25.9 tok/s with oQ4e + native MTP on matching M4 Pro hardware. `xhigh` adds reasoning tokens but does not cause the memory-bandwidth limit. |
| Qwen3.8 Flash-Next | Roughly 180B total parameters; even 2-bit weights are about 45 GB before runtime overhead, beyond the practical Metal envelope. |

An experimental Qwen3.8-27B oMLX recipe reaches 53 tok/s prose and 72 tok/s
code on an M4 Max by combining Neural Engine prefill and native MTP. The M4 Max
has roughly twice this machine's memory bandwidth, so that result is not evidence
for 50 tok/s here. Revisit Qwen3.8 only after a matching M4 Pro result clears the
Pi harness target, not merely a raw-server benchmark.

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
6. **Speed check:** measure both oMLX decode and Pi's end-to-end rate with the
   same prompt, tools, and context. The adoption target is at least 50 tok/s in
   representative Pi sessions, not merely a short raw-server generation.

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
