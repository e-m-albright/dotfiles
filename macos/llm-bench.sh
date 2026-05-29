#!/bin/bash
# Unified benchmark for local LLM runtimes.
# Wraps llama.cpp's llama-bench and LM Studio's /api/v0 stats endpoint
# so you can compare apples-to-apples across runtimes.
#
# Usage:
#   llm-bench lmstudio [MODEL_ID]              # bench a model loaded in LM Studio
#   llm-bench llamacpp -hf REPO:QUANT          # download + bench a HF GGUF
#   llm-bench llamacpp -m /path/to/model.gguf  # bench a local GGUF
#   llm-bench list                             # list loaded LM Studio models

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=print_utils.sh
source "$SCRIPT_DIR/print_utils.sh"

LMS_HOST="${LMS_HOST:-http://localhost:1234}"
PP_TOKENS="${PP_TOKENS:-128}"
TG_TOKENS="${TG_TOKENS:-128}"

bench_lmstudio() {
    local model="${1:-}"

    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq is required (brew install jq)"
        exit 1
    fi

    if [[ -z "$model" ]]; then
        model=$(curl -fsS "$LMS_HOST/api/v0/models" 2>/dev/null \
            | jq -r '.data[] | select(.state=="loaded") | .id' | head -1 || true)
        if [[ -z "$model" ]]; then
            print_error "No loaded model in LM Studio. Pass MODEL_ID or load one in the GUI."
            print_info "List with: lms ps"
            exit 1
        fi
        print_info "Auto-selected loaded model: $model"
    fi

    print_section "LM Studio — $model"

    # tg: short prompt, TG_TOKENS output. stats.tokens_per_second is gen-only.
    print_action "Token-gen run (tg${TG_TOKENS})..."
    local tg_json
    tg_json=$(curl -fsS "$LMS_HOST/api/v0/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "$(jq -n --arg m "$model" --argjson n "$TG_TOKENS" '{
            model:$m,
            messages:[{role:"user", content:"Count from 1 upwards, separated by spaces, until you are stopped."}],
            max_tokens:$n,
            temperature:0,
            stream:false
        }')")
    local tg_tps ttft gen_time
    tg_tps=$(echo "$tg_json" | jq -r '.stats.tokens_per_second // 0' | awk '{printf "%.2f", $1}')
    ttft=$(echo  "$tg_json" | jq -r '.stats.time_to_first_token // "n/a"')
    gen_time=$(echo "$tg_json" | jq -r '.stats.generation_time // "n/a"')

    # pp: PP_TOKENS-ish prompt, max_tokens=1 → TTFT ~= prompt eval time.
    print_action "Prompt-eval run (pp${PP_TOKENS})..."
    local prompt
    prompt=$(python3 -c "import random,string; print(' '.join(random.choices(string.ascii_lowercase, k=$PP_TOKENS)))")
    local pp_json
    pp_json=$(curl -fsS "$LMS_HOST/api/v0/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "$(jq -n --arg m "$model" --arg p "$prompt" '{
            model:$m,
            messages:[{role:"user", content:$p}],
            max_tokens:1,
            temperature:0,
            stream:false
        }')")
    local pp_ttft pp_gen pp_in_tokens pp_wall pp_tps
    pp_ttft=$(echo "$pp_json" | jq -r '.stats.time_to_first_token // 0')
    pp_gen=$(echo  "$pp_json" | jq -r '.stats.generation_time // 0')
    pp_in_tokens=$(echo "$pp_json" | jq -r '.usage.prompt_tokens // 0')
    # When max_tokens=1, LM Studio folds prompt-eval into generation_time
    # (ttft=0). Use whichever is larger as the prompt-eval wall time.
    pp_wall=$(awk -v a="$pp_ttft" -v b="$pp_gen" 'BEGIN{print (a>b)?a:b}')
    if awk -v w="$pp_wall" -v n="$pp_in_tokens" 'BEGIN{exit !(w>0 && n>0)}'; then
        pp_tps=$(awk -v n="$pp_in_tokens" -v t="$pp_wall" 'BEGIN{printf "%.2f", n/t}')
    else
        pp_tps="n/a"
    fi

    printf "\n"
    printf "  ${BOLD}Results${NC}\n"
    printf "    %-22s ${BOLD}%s${NC} tok/s   (%s prompt tokens / %ss eval)\n" "Prompt eval (pp):" "$pp_tps" "$pp_in_tokens" "$pp_wall"
    printf "    %-22s ${BOLD}%s${NC} tok/s   (%ss gen, %ss TTFT)\n" "Token gen (tg):"   "$tg_tps" "$gen_time" "$ttft"
}

bench_llamacpp() {
    if ! command -v llama-bench >/dev/null 2>&1; then
        print_error "llama-bench not found (brew install llama.cpp)"
        exit 1
    fi
    print_section "llama.cpp — $*"
    llama-bench -p "$PP_TOKENS" -n "$TG_TOKENS" "$@"
}

list_loaded() {
    if ! command -v lms >/dev/null 2>&1; then
        print_error "lms CLI not found. Install LM Studio + run 'lms bootstrap'."
        exit 1
    fi
    lms ps
}

usage() {
    cat <<'EOF'
llm-bench — unified local LLM benchmark

Usage:
  llm-bench lmstudio [MODEL_ID]         Bench loaded LM Studio model (auto if omitted)
  llm-bench llamacpp -hf REPO:QUANT     Download HF GGUF and bench
  llm-bench llamacpp -m /path/model.gguf  Bench local GGUF
  llm-bench list                        List loaded LM Studio models

Env:
  PP_TOKENS=128   Prompt tokens for prompt-eval phase
  TG_TOKENS=128   Tokens to generate for token-gen phase
  LMS_HOST=http://localhost:1234

Examples:
  llm-bench lmstudio
  llm-bench lmstudio qwen/qwen3.6-27b
  llm-bench llamacpp -hf bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M
EOF
}

cmd="${1:-}"
shift || true
case "$cmd" in
    lmstudio|lms) bench_lmstudio "$@" ;;
    llamacpp|llama) bench_llamacpp "$@" ;;
    list|ls)      list_loaded ;;
    ""|-h|--help) usage ;;
    *) print_error "Unknown subcommand: $cmd"; usage; exit 1 ;;
esac
