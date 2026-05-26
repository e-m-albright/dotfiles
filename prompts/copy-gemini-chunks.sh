#!/usr/bin/env bash
# Copy the Gemini-chunked advisor prompt into the macOS clipboard, one chunk
# at a time, in reverse order so Flycut's history ends up with chunk 01 on
# top. Open Flycut after running, then paste each chunk into Gemini's
# "Saved info" as a separate entry.
#
# Gemini's saved-info per-entry limit is ~1500 chars; each chunk fits.
# https://gemini.google.com/saved-info
#
# Usage:
#   prompts/copy-gemini-chunks.sh             # load all chunks into Flycut
#   prompts/copy-gemini-chunks.sh --step      # interactive — wait between
#                                               each chunk (press enter to
#                                               copy next; useful without
#                                               Flycut, paste as you go)
#   prompts/copy-gemini-chunks.sh --list      # show chunk filenames + sizes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHUNK_DIR="$SCRIPT_DIR/gemini-chunks"

if [[ -t 1 ]]; then
    BLUE='\033[0;34m'; GREEN='\033[0;32m'; DIM='\033[2m'; NC='\033[0m'
else
    BLUE=''; GREEN=''; DIM=''; NC=''
fi

if [[ ! -d "$CHUNK_DIR" ]]; then
    echo "error: chunk dir not found: $CHUNK_DIR" >&2
    exit 1
fi

# Sorted chunk list (lexicographic; the 0N prefix gives correct order).
mapfile -t CHUNKS < <(find "$CHUNK_DIR" -maxdepth 1 -name '*.md' | sort)

if [[ "${1:-}" == "--list" ]]; then
    printf "${BLUE}Gemini chunks${NC} (target: ~1500 chars each)\n\n"
    for f in "${CHUNKS[@]}"; do
        printf "  %4d chars  %s\n" "$(wc -c < "$f")" "$(basename "$f")"
    done
    exit 0
fi

if ! command -v pbcopy >/dev/null 2>&1; then
    echo "error: pbcopy not available (macOS only)" >&2
    exit 1
fi

if [[ "${1:-}" == "--step" ]]; then
    printf "${BLUE}Interactive mode${NC}: copy each chunk, paste into Gemini Saved Info, then press enter.\n"
    printf "Open https://gemini.google.com/saved-info in another window.\n\n"
    for f in "${CHUNKS[@]}"; do
        printf "${GREEN}Copying $(basename "$f")${NC} ($(wc -c < "$f") chars)\n"
        pbcopy < "$f"
        printf "  ${DIM}paste it as a new Saved Info entry, then press enter for next…${NC}"
        read -r
    done
    printf "\n${GREEN}done${NC} — all %d chunks copied.\n" "${#CHUNKS[@]}"
    exit 0
fi

# Default mode: pre-load all chunks into Flycut history. Reverse order so
# Flycut's most-recent (top of its history list) is chunk 01.
printf "${BLUE}Loading %d chunks into clipboard history (for Flycut)…${NC}\n" "${#CHUNKS[@]}"
for ((i = ${#CHUNKS[@]} - 1; i >= 0; i--)); do
    f="${CHUNKS[$i]}"
    pbcopy < "$f"
    printf "  ${GREEN}✓${NC}  %s (%d chars)\n" "$(basename "$f")" "$(wc -c < "$f")"
    # Flycut polls the clipboard; give it a beat to capture each one.
    sleep 0.4
done

cat <<'EOF'

Next:
  1. Open https://gemini.google.com/saved-info
  2. Open Flycut (default shortcut: cmd+shift+V)
  3. For each entry in Flycut history (top is chunk 01), click "Add new"
     in Gemini, paste, and save.

If your Flycut history didn't catch all 7, re-run with --step instead.
EOF
