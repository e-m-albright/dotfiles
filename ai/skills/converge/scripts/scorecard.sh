#!/usr/bin/env bash
# scorecard.sh — deterministic code-health scorecard for the convergence engine.
#
# Emits the ratchet metric set for the current git repo so Phase 1 (Measure) and
# Phase 6 (Report) compare apples to apples instead of re-improvising commands.
# Read-only: it never edits files. Safe to re-run.
#
# Core metrics (always, fast — git + grep only):
#   - LOC (cloc/tokei if present, else tracked-line count)
#   - suppression counts, per family
#   - churn × (file LOC) hotspots, top N
# Deep metrics (--deep, runs whatever analyzers are installed):
#   - cognitive complexity, duplication %, dependency cycles, dead code
#
# Usage:
#   scorecard.sh [--json] [--deep] [--since <git-date>] [--top <N>] [--help]
#
# Examples:
#   scorecard.sh                       # fast human-readable scorecard
#   scorecard.sh --json > before.json  # machine baseline for the ratchet
#   scorecard.sh --deep --since '3 months ago'
set -euo pipefail

JSON=0; DEEP=0; SINCE='6 months ago'; TOP=15
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1 ;;
    --deep) DEEP=1 ;;
    --since) SINCE="${2:?--since needs a value}"; shift ;;
    --top) TOP="${2:?--top needs a value}"; shift ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "scorecard: not inside a git repo" >&2; exit 1
fi
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

have() { command -v "$1" >/dev/null 2>&1; }

# ---- LOC ---------------------------------------------------------------------
loc_total() {
  if have cloc; then
    cloc --quiet --csv --sum-one . 2>/dev/null | awk -F, '/^[0-9]/{c+=$5} END{print c+0}'
  elif have tokei; then
    tokei --output json 2>/dev/null | grep -o '"code":[0-9]*' | awk -F: '{s+=$2} END{print s+0}'
  else
    # fallback: count lines of tracked text files
    git ls-files | while read -r f; do [ -f "$f" ] && wc -l <"$f" 2>/dev/null || true; done \
      | awk '{s+=$1} END{print s+0}'
  fi
}

# ---- suppression families ----------------------------------------------------
# name|regex (extended). Counted across tracked files via git grep.
SUPP_FAMILIES='
type-ignore|# *type: *ignore|// *@ts-(ignore|expect-error)
lint-disable|# *noqa|# *pyright: *ignore|eslint-disable|biome-ignore|svelte-ignore
allow-attr|#\[allow\(
broad-except|except Exception|except BaseException
any-type|dict\[str, *Any\]|: *Any\b|\bas any\b
cast-escape|\bcast\(|\.unwrap\(\)|\bas \![A-Za-z]
skipped-test|@pytest\.mark\.skip|\bit\.skip\b|\bdescribe\.skip\b|#\[ignore\]
todo|TODO|FIXME|XXX
no-cover|# *pragma: *no cover|c8 ignore|istanbul ignore'

supp_count() { # regex -> count (git grep exits 1 on no match; tolerate it under pipefail)
  { git grep -InE "$1" -- . 2>/dev/null || true; } | wc -l | tr -d ' '
}

# ---- churn x size hotspots ---------------------------------------------------
hotspots() {
  # churn = commits touching the file in window; weight by current line count.
  git log --since="$SINCE" --no-merges --name-only --format= -- . 2>/dev/null \
    | sed '/^$/d' | sort | uniq -c | sort -rn \
    | while read -r churn f; do
        [ -f "$f" ] || continue
        lines=$(wc -l <"$f" 2>/dev/null || echo 0)
        printf '%s\t%s\t%s\t%s\n' "$((churn*lines))" "$churn" "$lines" "$f"
      done | sort -rn | head -n "$TOP"
}

# ---- collect -----------------------------------------------------------------
LOC=$(loc_total)

SUPP_NAMES=(); SUPP_COUNTS=()
while IFS='|' read -r name re1 re2; do
  [ -n "${name:-}" ] || continue
  re="$re1"; [ -n "${re2:-}" ] && re="$re1|$re2"
  c=$(supp_count "$re")
  SUPP_NAMES+=("$name"); SUPP_COUNTS+=("$c")
done <<< "$(printf '%s\n' "$SUPP_FAMILIES" | sed '/^$/d')"

# ---- deep (optional) ---------------------------------------------------------
deep_report() {
  echo
  echo "## Deep metrics (installed analyzers)"
  local ran=0
  if have complexipy; then echo "- cognitive complexity (complexipy):"; complexipy . 2>/dev/null | tail -n 5 || true; ran=1; fi
  if have jscpd; then echo "- duplication (jscpd):"; jscpd --silent --reporters consoleFull . 2>/dev/null | tail -n 8 || true; ran=1; fi
  if have lint-imports; then echo "- import cycles (import-linter):"; lint-imports 2>/dev/null | tail -n 5 || true; ran=1; fi
  if have depcruise; then echo "- dependency cruiser available — run: depcruise --validate"; ran=1; fi
  if have madge; then echo "- circular deps (madge):"; madge --circular . 2>/dev/null | tail -n 8 || true; ran=1; fi
  if have knip; then echo "- dead code (knip): run \`knip\`"; ran=1; fi
  if have vulture; then echo "- dead code (vulture):"; vulture . 2>/dev/null | head -n 8 || true; ran=1; fi
  [ "$ran" = 0 ] && echo "  (none installed — see references/ONTOLOGY-AND-HIERARCHY.md for the per-language toolset)"
}

# ---- emit --------------------------------------------------------------------
if [ "$JSON" = 1 ]; then
  printf '{\n  "loc": %s,\n  "since": "%s",\n  "suppressions": {\n' "$LOC" "$SINCE"
  for i in "${!SUPP_NAMES[@]}"; do
    sep=','; [ "$i" -eq $(( ${#SUPP_NAMES[@]} - 1 )) ] && sep=''
    printf '    "%s": %s%s\n' "${SUPP_NAMES[$i]}" "${SUPP_COUNTS[$i]}" "$sep"
  done
  printf '  },\n  "hotspots": [\n'
  first=1
  while IFS=$'\t' read -r score churn lines f; do
    [ -n "${f:-}" ] || continue
    [ "$first" = 1 ] || printf ',\n'; first=0
    printf '    {"file": "%s", "score": %s, "churn": %s, "loc": %s}' "$f" "$score" "$churn" "$lines"
  done < <(hotspots)
  printf '\n  ]\n}\n'
  exit 0
fi

echo "# Code-health scorecard — $(git rev-parse --short HEAD) @ $ROOT"
echo
echo "Total LOC: $LOC"
echo
echo "## Suppressions (lower is better; ratchet each family down)"
for i in "${!SUPP_NAMES[@]}"; do printf '  %-14s %s\n' "${SUPP_NAMES[$i]}" "${SUPP_COUNTS[$i]}"; done
echo
echo "## Hotspots (churn×LOC, since \"$SINCE\", top $TOP) — spend effort here first"
printf '  %-8s %-6s %-6s %s\n' SCORE CHURN LOC FILE
hotspots | while IFS=$'\t' read -r score churn lines f; do
  printf '  %-8s %-6s %-6s %s\n' "$score" "$churn" "$lines" "$f"
done
[ "$DEEP" = 1 ] && deep_report
echo
echo "Tip: \`scorecard.sh --json > before.json\`, refactor, then diff against a fresh run."
