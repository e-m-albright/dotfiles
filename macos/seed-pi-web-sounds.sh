#!/bin/bash
# Seed ygncode/pi-web notification sounds from macOS system sounds.
#
# pi-web (the phone Pi PWA) scans <pi-agent>/pi-web/assets/*.mp3 and lists them
# in its in-app sound picker. Its two shipped defaults (cat/done) sound bad, so
# this overwrites them with pleasant system sounds and adds a curated set — all
# converted from /System/Library/Sounds. Reproducible: re-run on any Mac to
# regenerate the set; idempotent (always re-encodes the same curated list).
#
# Override the target dir with PI_WEB_ASSETS. macOS-only (needs the system
# sounds + ffmpeg for mp3 encoding, since pi-web only serves .mp3).
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=macos/print_utils.sh
source "$SCRIPT_DIR/print_utils.sh"

ASSETS="${PI_WEB_ASSETS:-$HOME/.pi/agent/pi-web/assets}"
SYS="/System/Library/Sounds"

print_section "pi-web notification sounds"

if ! command -v ffmpeg >/dev/null 2>&1; then
    print_error "ffmpeg not found (brew install ffmpeg) — cannot encode mp3"
    exit 1
fi
if [[ ! -d "$SYS" ]]; then
    print_error "macOS system sounds not found at $SYS (macOS-only script)"
    exit 1
fi

mkdir -p "$ASSETS"

count=0
# cat/done overwrite pi-web's two bad shipped defaults; the rest add picker options.
while IFS=: read -r out src; do
    if [[ -z "$out" ]]; then
        continue
    fi
    aiff="$SYS/$src.aiff"
    if [[ ! -f "$aiff" ]]; then
        print_warn "system sound missing: $src.aiff (skipped)"
        continue
    fi
    if ffmpeg -nostdin -y -i "$aiff" -codec:a libmp3lame -q:a 4 -ar 44100 "$ASSETS/$out.mp3" >/dev/null 2>&1; then
        print_step "$out.mp3 ← $src"
        count=$((count + 1))
    else
        print_error "failed to encode $out.mp3 from $src"
    fi
done <<'EOF'
cat:Glass
done:Hero
glass:Glass
hero:Hero
ping:Ping
submarine:Submarine
pop:Pop
tink:Tink
purr:Purr
sosumi:Sosumi
blow:Blow
bottle:Bottle
EOF

print_success "Seeded $count sounds into $ASSETS"
print_dim "Refresh the pi-web PWA and pick one in its sound settings."
