#!/usr/bin/env bash
# Configure Pi (pi.dev / earendil-works) — local-first terminal agent. Idempotent.
#
# Re-added narrowly per docs/adr/0005 — for local LM Studio + lightweight
# terminal loops + headless automation. See ADR-0005 and ADR-0003 for context.
#
# Pi reads:
#   ~/.pi/agent/settings.json   # defaults (symlinked from here)
#   ~/.pi/agent/models.json     # providers incl. LM Studio (symlinked from here)
#   ~/.pi/agent/AGENTS.md       # global instructions (baked rules, like Codex)
#   ~/.agents/skills/           # shared skills (deployed by Codex setup via `npx skills`)
#   ~/.pi/agent/agents/*.md     # subagents (read by the pi-subagent extension)
#   ~/.pi/agent/extensions/*.ts # local extensions (symlinked from agents/pi/extensions/)

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"
PI_HOME="$HOME/.pi/agent"

source "$SHARED_DIR/lib.sh"
agentlib_init "$@"

# --- Ensure the `pi` binary exists. Global npm installs are per-node-version,
#     so an fnm/nvm node bump silently orphans it (config survives, binary
#     vanishes). Self-heal instead of skipping quietly. ---
PI_NPM_PKG="@earendil-works/pi-coding-agent"  # renamed from @mariozechner/* (that scope is frozen)
if ! command -v pi >/dev/null 2>&1; then
    if command -v npm >/dev/null 2>&1; then
        print_action "Pi binary not found — installing $PI_NPM_PKG globally…" 2>/dev/null || \
            print_info "Pi binary not found — installing $PI_NPM_PKG globally…"
        if npm install -g "$PI_NPM_PKG" >/dev/null 2>&1; then
            hash -r 2>/dev/null || true
            print_success "Installed pi ($PI_NPM_PKG)"
        else
            print_warning "Pi install failed — run manually: npm install -g $PI_NPM_PKG"
            return 0 2>/dev/null || exit 0
        fi
    else
        print_warning "Pi not installed and npm unavailable — skipping (install: npm install -g $PI_NPM_PKG)"
        return 0 2>/dev/null || exit 0
    fi
fi

mkdir -p "$PI_HOME"

# --- Config: defaults + providers (symlinked) ---
ln -sf "$SCRIPT_DIR/settings.json" "$PI_HOME/settings.json"
ln -sf "$SCRIPT_DIR/models.json" "$PI_HOME/models.json"
print_success "Linked Pi settings + models.json (LM Studio provider)"

# --- Global instructions (AGENTS.md) — baked rules, same source as Codex ---
if [[ -f "$SHARED_DIR/rules.md" ]]; then
    # shellcheck source=../shared/bake-rules.sh
    source "$SHARED_DIR/bake-rules.sh"
    {
        echo "# Global Agent Instructions"
        echo ""
        cat "$SHARED_DIR/rules.md"
        echo ""
        bake_rules "$DOTFILES_DIR"
    } > "$PI_HOME/AGENTS.md"
    print_success "Global instructions + baked rules (~/.pi/agent/AGENTS.md)"
fi

# --- Subagents (shared deployer) ---
deploy_subagents "$PI_HOME/agents"

# --- Extensions (symlinked so edits are live after /reload) ---
if [[ -d "$SCRIPT_DIR/extensions" ]]; then
    mkdir -p "$PI_HOME/extensions"
    find "$PI_HOME/extensions" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
    ext_count=0
    for extension in "$SCRIPT_DIR"/extensions/*.ts; do
        [[ -f "$extension" ]] || continue
        ln -sf "$extension" "$PI_HOME/extensions/$(basename "$extension")"
        ext_count=$((ext_count + 1))
    done
    [[ $ext_count -gt 0 ]] && print_success "Linked $ext_count Pi extensions (~/.pi/agent/extensions/)"
fi

# --- Skills note: shared via ~/.agents/skills (deployed by Codex setup) ---
if [[ -d "$HOME/.agents/skills" ]]; then
    sk=$(find "$HOME/.agents/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    print_skip "Skills shared via ~/.agents/skills ($sk available — deployed by Codex setup)"
fi

# --- Superpowers-equivalent (THIRD-PARTY package — runs with full permissions) ---
# Approved 2026-05-25 (ADR-0005). Comment this block to opt out.
if pi list 2>/dev/null | grep -q "pi-superpowers-plus"; then
    print_skip "pi-superpowers-plus already installed"
else
    print_action "Installing pi-superpowers-plus (third-party Superpowers port)…" 2>/dev/null || \
        print_info "Installing pi-superpowers-plus (third-party Superpowers port)…"
    if pi install npm:pi-superpowers-plus >/dev/null 2>&1; then
        print_success "Installed pi-superpowers-plus"
    else
        print_warning "Install failed — run manually: pi install npm:pi-superpowers-plus"
    fi
fi

# --- mitsupi (Armin Ronacher's commands/skills/extensions — full permissions) ---
# Approved 2026-05-25 (ADR-0006). Comment this block to opt out.
if pi list 2>/dev/null | grep -q "mitsupi"; then
    print_skip "mitsupi already installed"
else
    print_action "Installing mitsupi (Armin Ronacher's pi kit)…" 2>/dev/null || \
        print_info "Installing mitsupi (Armin Ronacher's pi kit)…"
    if pi install npm:mitsupi >/dev/null 2>&1; then
        print_success "Installed mitsupi"
    else
        print_warning "Install failed — run manually: pi install npm:mitsupi"
    fi
fi
