#!/bin/bash
# Evaluate local LLMs in LM Studio: throughput, TTFT, context fit, head-to-head.
# Encodes the methodology + heuristics from docs/local-llm-stack.md.
#
# Usage:
#   llm-bench list                      List loaded LM Studio models
#   llm-bench bench [MODEL_ID]          Bench currently-loaded (or specified) model
#   llm-bench estimate MODEL_ID [CTX]   Memory estimate at given context (default 262144)
#   llm-bench compare MODEL_A MODEL_B   Head-to-head, same prompt, same conditions
#
# Targets on M4 Pro 48GB:
#   > 40 tok/s gen = usable for interactive agentic work
#   > 100 tok/s    = usable for autocomplete-style tasks
#   < 20 tok/s     = painful, reconsider the model

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=print_utils.sh
source "$SCRIPT_DIR/print_utils.sh"

LMS_HOST="${LMS_HOST:-http://localhost:1234}"
PP_TOKENS="${PP_TOKENS:-128}"
TG_TOKENS="${TG_TOKENS:-256}"
LOAD_CTX="${LOAD_CTX:-32768}"

# Standardized coding prompt — non-trivial enough to expose reasoning tax,
# small enough that a fast model finishes in seconds.
BENCH_PROMPT='Write a Python function `first_n_primes(n)` returning the first N prime numbers using the Sieve of Eratosthenes. Include a brief docstring and one test case. Keep it under 20 lines total.'

require_deps() {
    for cmd in jq python3 curl; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            print_error "$cmd is required"
            exit 1
        fi
    done
}

list_loaded() {
    if ! command -v lms >/dev/null 2>&1; then
        print_error "lms CLI not found. Install LM Studio + run 'lms bootstrap'."
        exit 1
    fi
    lms ps
}

current_loaded_id() {
    curl -fsS "$LMS_HOST/api/v0/models" 2>/dev/null \
        | jq -r '.data[] | select(.state=="loaded") | .id' | head -1
}

ensure_loaded() {
    local model="$1"
    local loaded
    loaded=$(current_loaded_id)
    if [[ "$loaded" != "$model" ]]; then
        print_action "Loading $model at ${LOAD_CTX} context..."
        lms unload --all >/dev/null 2>&1
        lms load "$model" -c "$LOAD_CTX" -y >/dev/null 2>&1
    fi
}

bench_one() {
    local model="$1"
    require_deps

    if [[ -n "$model" ]]; then
        ensure_loaded "$model"
    else
        model=$(current_loaded_id)
        if [[ -z "$model" ]]; then
            print_error "No model loaded. Pass MODEL_ID or load one first."
            exit 1
        fi
        print_info "Benching currently-loaded: $model"
    fi

    print_section "$model"

    # Warm-up (eliminates first-load TTFT spike)
    curl -fsS "$LMS_HOST/api/v0/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "$(jq -n --arg m "$model" '{model:$m, messages:[{role:"user", content:"hi"}], max_tokens:8, temperature:0}')" \
        >/dev/null

    # Token-gen run
    print_action "Token-gen (tg${TG_TOKENS}, real coding prompt)..."
    local tg_file
    tg_file=$(mktemp)
    curl -fsS "$LMS_HOST/api/v0/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "$(jq -n --arg m "$model" --arg p "$BENCH_PROMPT" --argjson n "$TG_TOKENS" \
            '{model:$m, messages:[{role:"user", content:$p}], max_tokens:$n, temperature:0, stream:false}')" \
        > "$tg_file"

    # Prompt-eval run (PP_TOKENS random prompt, max_tokens=1)
    print_action "Prompt-eval (pp${PP_TOKENS})..."
    local prompt
    prompt=$(python3 -c "import random,string; print(' '.join(random.choices(string.ascii_lowercase, k=$PP_TOKENS)))")
    local pp_file
    pp_file=$(mktemp)
    curl -fsS "$LMS_HOST/api/v0/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "$(jq -n --arg m "$model" --arg p "$prompt" \
            '{model:$m, messages:[{role:"user", content:$p}], max_tokens:1, temperature:0, stream:false}')" \
        > "$pp_file"

    # Report
    python3 - "$tg_file" "$pp_file" "$model" <<'PYEOF'
import json, sys
tg = json.load(open(sys.argv[1]))
pp = json.load(open(sys.argv[2]))
model = sys.argv[3]

tg_stats = tg.get('stats', {})
pp_stats = pp.get('stats', {})
tg_tps = tg_stats.get('tokens_per_second', 0) or 0
ttft = tg_stats.get('time_to_first_token', 0) or 0
gen_time = tg_stats.get('generation_time', 0) or 0
reasoning = tg.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens', 0) or 0
completion = tg.get('usage', {}).get('completion_tokens', 0) or 0
content_len = len(tg.get('choices', [{}])[0].get('message', {}).get('content', '') or '')

pp_ttft = pp_stats.get('time_to_first_token', 0) or 0
pp_gen = pp_stats.get('generation_time', 0) or 0
pp_in = pp.get('usage', {}).get('prompt_tokens', 0) or 0
pp_wall = max(pp_ttft, pp_gen)
pp_tps = (pp_in / pp_wall) if pp_wall > 0 and pp_in > 0 else 0

def classify(tps):
    if tps >= 100: return "autocomplete-grade"
    if tps >= 40:  return "interactive-grade"
    if tps >= 20:  return "tolerable"
    return "painful"

print()
print(f"  Throughput")
print(f"    Token gen (tg):       {tg_tps:6.2f} tok/s   [{classify(tg_tps)}]")
print(f"    Prompt eval (pp):     {pp_tps:6.2f} tok/s   ({pp_in} tokens / {pp_wall:.2f}s)")
print(f"    TTFT (warm):          {ttft:6.3f}s")
print()
print(f"  Reasoning-mode check")
print(f"    Reasoning tokens:     {reasoning}")
print(f"    Visible content len:  {content_len} chars")
if reasoning > 0:
    print(f"    -> THINKING MODEL — budget {3 + (reasoning // 100)}x max_tokens for visible output")
PYEOF

    rm -f "$tg_file" "$pp_file"
}

estimate_ctx() {
    local model="$1"
    local ctx="${2:-262144}"
    if [[ -z "$model" ]]; then
        print_error "Usage: llm-bench estimate MODEL_ID [CTX]"
        exit 1
    fi
    print_section "$model @ $(awk -v c="$ctx" 'BEGIN{printf "%.0fK", c/1024}') context"
    lms load "$model" -c "$ctx" --estimate-only -y 2>&1 | grep -iE "estimate|memory" | head -3
    echo ""
    echo "  Working set ceiling on M4 Pro 48GB: ~40 GB"
}

compare_two() {
    local a="$1" b="$2"
    if [[ -z "$a" || -z "$b" ]]; then
        print_error "Usage: llm-bench compare MODEL_A MODEL_B"
        exit 1
    fi
    print_header "Head-to-head: $a vs $b"
    bench_one "$a"
    echo ""
    bench_one "$b"
    echo ""
    print_info "Per the local-llm-stack.md heuristic:"
    print_info "  > 40 tok/s = interactive-grade; > 100 = autocomplete-grade"
}

usage() {
    cat <<'EOF'
llm-bench — evaluate local LM Studio models

Usage:
  llm-bench list                       List currently-loaded models
  llm-bench bench [MODEL_ID]           Bench currently-loaded (or specified) model
  llm-bench estimate MODEL_ID [CTX]    Memory estimate at given context (default 256K)
  llm-bench compare MODEL_A MODEL_B    Head-to-head comparison

Env:
  LMS_HOST=http://localhost:1234       LM Studio endpoint
  LOAD_CTX=32768                       Context to load test models at
  PP_TOKENS=128                        Prompt tokens for prompt-eval phase
  TG_TOKENS=256                        Tokens to generate for token-gen phase

Reading the output:
  tok/s tiers (M4 Pro 48GB):
    > 100  = autocomplete-grade (1B-class models)
    > 40   = interactive-grade  (MoE-with-3B-active, well-quantized 7B)
    > 20   = tolerable          (dense 14B, big MoE)
    < 20   = painful            (dense 27B+ on this hardware)

  Reasoning tokens > 0 means the model is a thinking model; visible output
  shows up only after that many tokens are generated. Budget 3-5x max_tokens.

See: docs/local-llm-stack.md
EOF
}

cmd="${1:-}"
shift || true
case "$cmd" in
    list|ls)         list_loaded ;;
    bench|b)         bench_one "${1:-}" ;;
    estimate|est)    estimate_ctx "${1:-}" "${2:-262144}" ;;
    compare|cmp)     compare_two "${1:-}" "${2:-}" ;;
    ""|-h|--help)    usage ;;
    *)               print_error "Unknown subcommand: $cmd"; usage; exit 1 ;;
esac
