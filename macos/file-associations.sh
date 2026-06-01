#!/usr/bin/env bash
# Set default apps for common file types via duti.
# Idempotent — safe to re-run.
#
# Sourced by install.sh after brew install (which installs duti).
#
# Why this exists: macOS double-clicking a text, markdown, or source/config
# file used to open Cursor, which is slow to cold-start. Routing to Zed (Rust,
# GPU-rendered) gives a noticeably faster read-and-close experience. QLMarkdown
# handles the spacebar-Quick-Look case for .md previews without opening anything.

set -eo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Only source print_utils if not already loaded (install.sh sources it once).
if ! declare -f print_step >/dev/null 2>&1; then
    source "$DOTFILES_DIR/macos/print_utils.sh"
fi

if ! command -v duti >/dev/null 2>&1; then
    print_warning "duti not installed — skipping file associations (install via packages.toml)"
    return 0 2>/dev/null || exit 0
fi

# Read bundle id from Info.plist (works even when the app isn't running).
read_bundle_id() {
    local app_path="$1"
    if [[ -f "$app_path/Contents/Info.plist" ]]; then
        defaults read "$app_path/Contents/Info.plist" CFBundleIdentifier 2>/dev/null
    fi
}

set_default() {
    local bundle_id="$1" type="$2" label="$3"
    # `duti -x` lists current default; match the bundle id to detect no-op.
    if duti -x "$type" 2>/dev/null | grep -qx "$bundle_id"; then
        print_skip "$label: $type → already set"
        return
    fi
    if duti -s "$bundle_id" "$type" all 2>/dev/null; then
        print_success "$label: $type → $bundle_id"
    else
        print_warning "$label: could not set $type → $bundle_id"
    fi
}

# --- Zed for text, markdown, and source/config files ---
# Anything a person edits in a code editor routes to Zed, not Cursor. Browser
# (.html/.js/.svg), Quick-Look-only, and document types (.csv/.log) are left
# to their own defaults — only editor-owned types are claimed here.
ZED_UTIS=(
    public.plain-text
    net.daringfireball.markdown
    public.yaml
    org.yaml
    com.apple.yaml
    public.json
    org.vuejs.vue  # .vue has a real exported UTI; Cursor claims the bare
                   # extension as Owner, so set the UTI to win the handoff.
)
ZED_EXTENSIONS=(
    md txt
    yaml yml json toml ini cfg
    scss less cjs jsx ts tsx
    py rb rs go c h cpp hpp cc java swift php lua sql bash dockerfile
)
ZED_ID="$(read_bundle_id /Applications/Zed.app)"
if [[ -n "$ZED_ID" ]]; then
    for uti in "${ZED_UTIS[@]}"; do
        set_default "$ZED_ID" "$uti" "Zed"
    done
    for ext in "${ZED_EXTENSIONS[@]}"; do
        set_default "$ZED_ID" ".$ext" "Zed"
    done
else
    print_warning "Zed not found at /Applications/Zed.app, skipping text-file associations"
fi

# --- Quick Look extensions (sbarex) ---
# Modern .appex Quick Look extensions register with macOS only after the host
# app has launched at least once. We can't auto-launch in a headless install,
# so we surface the one-time step. Both apps are tiny preference panes; quit
# immediately after launch.
ql_apps=(
    "QLMarkdown.app"      # rendered markdown
    "Syntax Highlight.app" # code / yaml / toml / json / cfg / ...
)
need_launch=()
for app in "${ql_apps[@]}"; do
    if [[ -d "/Applications/$app/Contents/PlugIns" ]]; then
        need_launch+=("$app")
    fi
done

if [[ ${#need_launch[@]} -gt 0 ]]; then
    print_success "Quick Look plugins installed: ${need_launch[*]}"
    print_info "  if spacebar previews aren't styled, register the extensions:"
    for app in "${need_launch[@]}"; do
        print_step "    open \"/Applications/$app\"   # launch once, quit, done"
    done
    print_step "    qlmanage -r && qlmanage -r cache    # refresh QL cache"
fi
