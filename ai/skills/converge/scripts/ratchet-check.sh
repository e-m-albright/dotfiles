#!/usr/bin/env bash
# ratchet-check.sh — enforce a docs/health/<scope>/baselines.json ratchet.
#
# Counts current suppressions (per the patterns recorded in the baseline) and
# fails if any family exceeds its ceiling. Run from the dir the baseline's
# `files_glob` is relative to (its `run_from`, e.g. cli/). Read-only unless
# --update is passed.
#
# Usage:
#   ratchet-check.sh <baselines.json>            # check; exit 1 on any regression
#   ratchet-check.sh <baselines.json> --update   # lower ceilings to current actuals
#
# The ratchet is monotonic: --update only ever LOWERS a ceiling, never raises.
set -euo pipefail

BASELINE="${1:?usage: ratchet-check.sh <baselines.json> [--update]}"
MODE="${2:-check}"
[ -f "$BASELINE" ] || { echo "no baseline at $BASELINE" >&2; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git repo" >&2; exit 2; }

# Count current matches for a regex across the baseline's files_glob, excluding tests.
# The glob carries `:(glob)` magic so `**` spans directories AND matches files
# directly under a prefix — a plain `src/**/*.py` pathspec silently skips `src/x.py`.
count() { # regex -> count of matches outside test files (awk never exits non-zero)
  { git grep -InE "$1" -- ":(glob)$GLOB" 2>/dev/null || true; } | awk '!/test_/{n++} END{print n+0}'
}

GLOB="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("files_glob","**/*"))' "$BASELINE")"

# Pull (family, pattern, ceiling) triples out of the baseline.
mapfile -t ROWS < <(python3 -c '
import json, sys
b = json.load(open(sys.argv[1]))
sup = b.get("suppressions", {})
pat = b.get("suppression_patterns", {})
for fam, ceil in sup.items():
    if fam in pat:
        print(f"{fam}\t{pat[fam]}\t{ceil}")
' "$BASELINE")

regressions=0
declare -A ACTUAL
printf '%-18s %8s %8s   %s\n' FAMILY CEILING ACTUAL STATUS
for row in "${ROWS[@]}"; do
  IFS=$'\t' read -r fam pat ceil <<< "$row"
  actual=$(count "$pat")
  ACTUAL[$fam]=$actual
  if [ "$actual" -gt "$ceil" ]; then
    status="✗ REGRESSED (+$((actual - ceil)))"; regressions=$((regressions + 1))
  elif [ "$actual" -lt "$ceil" ]; then
    status="↓ improved (-$((ceil - actual)))"
  else
    status="✓ at ceiling"
  fi
  printf '%-18s %8s %8s   %s\n' "$fam" "$ceil" "$actual" "$status"
done

if [ "$MODE" = "--update" ]; then
  # Lower ceilings to current actuals (never raise).
  pairs=()
  for k in "${!ACTUAL[@]}"; do pairs+=("$k=${ACTUAL[$k]}"); done
  python3 -c '
import json, sys
path, *pairs = sys.argv[1:]
b = json.load(open(path))
sup = b["suppressions"]
for kv in pairs:
    fam, val = kv.split("=", 1)
    if fam in sup:
        sup[fam] = min(sup[fam], int(val))
json.dump(b, open(path, "w"), indent=2)
open(path, "a").write("\n")
' "$BASELINE" "${pairs[@]}"
  echo "updated $BASELINE (ceilings lowered to current actuals; none raised)"
  exit 0
fi

echo
if [ "$regressions" -gt 0 ]; then
  echo "RATCHET FAILED: $regressions family(ies) above ceiling. Fix, or justify a Ratchet-Bump." >&2
  exit 1
fi
echo "ratchet OK — nothing above ceiling."
