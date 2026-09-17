#!/usr/bin/env bash
# Keep OrbStack on-demand instead of resident. Idempotent — safe to re-run.
#
# Sourced by install.sh after brew install (which installs the `orbstack` cask).
#
# Why this exists: OrbStack ships with `app.start_at_login = true`, so the Linux
# VM boots at login and stays resident whether or not containers are running —
# ~2 GB RSS and a background CPU tick, all day, on battery. Container work is
# occasional here, so the VM should start when asked and not before.
#
# This only changes *when* OrbStack runs, never whether it is installed;
# packages.toml remains the source of truth for that. Start it on demand with
# `orb start`; `docker` and `orb` subcommands also start it automatically.

set -eo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Only source print_utils if not already loaded (install.sh sources it once).
if ! declare -f print_step >/dev/null 2>&1; then
    source "$DOTFILES_DIR/macos/print_utils.sh"
fi

print_section "OrbStack (on-demand containers)"

if ! command -v orb >/dev/null 2>&1; then
    print_skip "orb CLI not found — install the orbstack cask, then re-run \`dotfiles install\`"
    return 0 2>/dev/null || exit 0
fi

if [[ "$(orb config get app.start_at_login 2>/dev/null)" == "false" ]]; then
    print_skip "OrbStack already on-demand (start_at_login=false)"
else
    if orb config set app.start_at_login false >/dev/null 2>&1; then
        print_success "OrbStack will no longer start at login"
    else
        print_warn "Could not set app.start_at_login — check \`orb config show\`"
    fi
fi

print_info "  Start it when you need containers: orb start   (stop with: orb stop)"
