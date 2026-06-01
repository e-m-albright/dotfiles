#!/usr/bin/env bash
# Configure the local LLM in LM Studio: ensure the model is downloaded and pin
# its context window. Idempotent — safe to re-run.
#
# Sourced by install.sh after brew install (which installs the `lm-studio` cask).
#
# Why this exists: LM Studio loads models at a conservative 4096-token context
# by default, which is far too small for agent system prompts (Zed's coding
# agent alone sends ~10.5K tokens of system prompt + tool schemas before you
# type anything). We pin a usable window here so harnesses don't overflow.
#
# NOTE: the `lms` CLI only exists after LM Studio has been launched once (it
# bootstraps ~/.lmstudio/bin/lms). On a fresh machine this step skips with a
# hint until the app has run once.

set -eo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Only source print_utils if not already loaded (install.sh sources it once).
if ! declare -f print_step >/dev/null 2>&1; then
    source "$DOTFILES_DIR/macos/print_utils.sh"
fi

# --- Config (edit these to change the local model / context window) ---
LMSTUDIO_MODEL="google/gemma-4-e4b"   # Gemma 4 e4b (effective ~4B), fast on Apple Silicon
LMSTUDIO_CONTEXT=32768                 # tokens to load at; model max is 131072

LMS="$HOME/.lmstudio/bin/lms"
[[ -x "$LMS" ]] || LMS="$(command -v lms 2>/dev/null || true)"

print_section "LM Studio (local LLM)"

if [[ -z "$LMS" || ! -x "$LMS" ]]; then
    print_skip "lms CLI not found — open LM Studio once (bootstraps the CLI), then re-run \`dotfiles install\`"
    return 0 2>/dev/null || exit 0
fi

# 1. Ensure the model is downloaded (skip if present).
if "$LMS" ls 2>/dev/null | grep -qi "${LMSTUDIO_MODEL##*/}"; then
    print_skip "Model already downloaded: $LMSTUDIO_MODEL"
else
    print_action "Downloading $LMSTUDIO_MODEL (multi-GB pull — one time)…"
    if "$LMS" get "$LMSTUDIO_MODEL" -y; then
        print_success "Downloaded $LMSTUDIO_MODEL"
    else
        print_warning "Could not download $LMSTUDIO_MODEL — pull it from the LM Studio app, then re-run"
        return 0 2>/dev/null || exit 0
    fi
fi

# 2. Pin the context window (load at $LMSTUDIO_CONTEXT if not already).
if "$LMS" ps 2>/dev/null | grep "$LMSTUDIO_MODEL" | grep -qw "$LMSTUDIO_CONTEXT"; then
    print_skip "Context already pinned: $LMSTUDIO_MODEL @ ${LMSTUDIO_CONTEXT} tokens"
else
    "$LMS" unload --all >/dev/null 2>&1 || true
    if "$LMS" load "$LMSTUDIO_MODEL" -c "$LMSTUDIO_CONTEXT" -y >/dev/null 2>&1; then
        print_success "Loaded $LMSTUDIO_MODEL @ ${LMSTUDIO_CONTEXT}-token context"
    else
        print_warning "Could not load model — start the LM Studio server, then re-run"
    fi
fi

print_info "  Pin it in the app too: LM Studio → My Models → $LMSTUDIO_MODEL → Context Length = $LMSTUDIO_CONTEXT"
print_info "  (so just-in-time reloads don't revert to the 4096 default)"
