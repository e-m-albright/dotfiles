#!/usr/bin/env bash
# perf-check.sh — enforce a performance-budget ratchet from a perf-baselines.json.
#
# The perf twin of ratchet-check.sh. Benchmarks each command with hyperfine and
# fails if its mean time regresses past the baseline + a tolerance band (perf
# numbers are noisy, so the gate is a band, not an exact ceiling). --update lowers
# baselines to current means — speedups lock in; a deliberate regression needs a
# justified manual bump. Baselines are ENVIRONMENT-SPECIFIC: re-baseline with
# --update on the target machine / CI runner. Slow + noisy, so it is NOT a
# pre-commit gate — run it manually or nightly.
#
# Usage:
#   perf-check.sh <perf-baselines.json>            # check; exit 1 on regression
#   perf-check.sh <perf-baselines.json> --update   # set baselines to current (lower only)
set -euo pipefail

BASELINE="${1:?usage: perf-check.sh <perf-baselines.json> [--update]}"
MODE="${2:-check}"
[ -f "$BASELINE" ] || { echo "no perf baseline at $BASELINE" >&2; exit 2; }
command -v hyperfine >/dev/null 2>&1 || {
  echo "perf-check: hyperfine not installed (brew install hyperfine)" >&2; exit 2; }

cfg() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], sys.argv[3]))' "$BASELINE" "$1" "$2"; }
WARMUP="$(cfg warmup 2)"
RUNS="$(cfg runs 10)"
TOL="$(cfg tolerance_pct 15)"

# Measure one command's mean wall time in ms via hyperfine's JSON export.
measure() { # command -> mean_ms | "ERR"
  local tmp; tmp="$(mktemp)"
  if ! hyperfine --warmup "$WARMUP" --runs "$RUNS" --export-json "$tmp" "$1" >/dev/null 2>&1; then
    rm -f "$tmp"; echo "ERR"; return
  fi
  python3 -c 'import json,sys; print(round(json.load(open(sys.argv[1]))["results"][0]["mean"]*1000, 1))' "$tmp"
  rm -f "$tmp"
}

# Pull (name, command, baseline_ms) rows out of the baseline.
mapfile -t ROWS < <(python3 -c '
import json, sys
b = json.load(open(sys.argv[1]))
for bm in b.get("benchmarks", []):
    base = bm.get("baseline_ms")
    print(bm["name"], bm["command"], "" if base is None else base, sep="\t")
' "$BASELINE")

regressions=0
declare -A ACTUAL
printf '%-18s %10s %10s %7s   %s\n' NAME BUDGET_ms ACTUAL_ms TOL STATUS
for row in "${ROWS[@]}"; do
  IFS=$'\t' read -r name cmd base <<< "$row"
  actual="$(measure "$cmd")"
  if [ "$actual" = "ERR" ]; then
    echo "$name: command failed: $cmd" >&2; regressions=$((regressions + 1)); continue
  fi
  ACTUAL["$name"]="$actual"
  if [ -z "$base" ]; then
    printf '%-18s %10s %10s %6s%%   %s\n' "$name" "—" "$actual" "$TOL" "○ no baseline (run --update)"
    continue
  fi
  budget="$(python3 -c 'import sys; print(round(float(sys.argv[1])*(1+float(sys.argv[2])/100),1))' "$base" "$TOL")"
  status="$(python3 -c '
import sys
base, actual, budget = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
if actual > budget: print(f"REG +{actual-base:.1f}ms over baseline")
elif actual < base: print(f"faster -{base-actual:.1f}ms")
else: print("within budget")
' "$base" "$actual" "$budget")"
  case "$status" in
    REG*) regressions=$((regressions + 1)); mark="✗ $status" ;;
    *) mark="✓ $status" ;;
  esac
  printf '%-18s %10s %10s %6s%%   %s\n' "$name" "$budget" "$actual" "$TOL" "$mark"
done

if [ "$MODE" = "--update" ]; then
  pairs=()
  for k in "${!ACTUAL[@]}"; do pairs+=("$k=${ACTUAL[$k]}"); done
  python3 -c '
import json, sys
path, *pairs = sys.argv[1:]
b = json.load(open(path))
vals = dict(p.split("=", 1) for p in pairs)
for bm in b["benchmarks"]:
    a = vals.get(bm["name"])
    if a is None:
        continue
    a = float(a)
    cur = bm.get("baseline_ms")
    bm["baseline_ms"] = round(min(cur, a) if cur is not None else a, 1)
json.dump(b, open(path, "w"), indent=2)
open(path, "a").write("\n")
' "$BASELINE" "${pairs[@]}"
  echo "updated $BASELINE (baselines lowered to current means; none raised)"
  exit 0
fi

echo
if [ "$regressions" -gt 0 ]; then
  echo "PERF BUDGET FAILED: $regressions benchmark(s) over budget. Optimize, or justify a baseline bump." >&2
  exit 1
fi
echo "perf OK — all within budget."
