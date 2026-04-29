#!/usr/bin/env bash
# scripts/audit/security.sh — runs deterministic security tools and aggregates
# findings into raw.json under .ai/artifacts/audits/security/<ts>/.
#
# Tools (free): osv-scanner, gitleaks, semgrep, trivy. Add language-specific
# scanners (cargo-deny, pip-audit, bandit, etc.) per the project's stacks.
#
# Each tool runs in isolation. If a tool is not installed, the entry records
# `status: "not-installed"` with the install command — fail-loud, not fail-silent.
# The LLM synthesis pass downstream reads raw.json and produces findings.md.
#
# Usage:  scripts/audit/security.sh [run-dir]

set -eo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TS="$(date -u +%Y-%m-%d-%H%M)"
RUN_DIR="${1:-.ai/artifacts/audits/security/$TS}"
mkdir -p "$RUN_DIR"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TOOLS_JSON="$(mktemp)"
echo "[]" > "$TOOLS_JSON"

# Append a tool entry to TOOLS_JSON.
record() {
    local name="$1" status="$2" out_file="$3" err_msg="$4" dur="$5" install="$6"
    local entry
    entry="$(jq -n \
        --arg name "$name" --arg status "$status" --arg out_file "$out_file" \
        --arg err_msg "$err_msg" --arg dur "${dur:-0}" --arg install "$install" \
        '{name: $name, status: $status, output_file: $out_file, error: $err_msg,
          duration_ms: ($dur | tonumber? // 0), install_cmd: $install}')"
    [[ -z "$entry" ]] && return 0
    jq --argjson e "$entry" '. + [$e]' "$TOOLS_JSON" > "${TOOLS_JSON}.tmp"
    mv "${TOOLS_JSON}.tmp" "$TOOLS_JSON"
}

# Run a tool with timing. Captures stdout to file; classifies result by:
#   1. binary missing → not-installed
#   2. exit 0 → ok
#   3. exit non-zero AND output is valid JSON → findings
#   4. exit non-zero AND output is not JSON → error
run_tool() {
    local name="$1" install="$2" out_rel="$3"
    shift 3
    if ! command -v "$1" >/dev/null 2>&1; then
        record "$name" "not-installed" "" "" 0 "$install"
        echo "  ✗ $name: not installed (install with: $install)" >&2
        return 0
    fi
    local out="$RUN_DIR/$out_rel"
    local start_ms end_ms dur_ms
    start_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
    if "$@" > "$out" 2>&1; then
        end_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
        dur_ms=$((end_ms - start_ms))
        record "$name" "ok" "$out_rel" "" "$dur_ms" ""
        echo "  ✓ $name: $out_rel (${dur_ms}ms)" >&2
    else
        end_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
        dur_ms=$((end_ms - start_ms))
        if [[ -s "$out" ]] && jq -e . "$out" >/dev/null 2>&1; then
            record "$name" "findings" "$out_rel" "" "$dur_ms" ""
            echo "  ⚠ $name: findings present in $out_rel (${dur_ms}ms)" >&2
        else
            local err_excerpt
            err_excerpt="$(head -c 500 "$out" 2>/dev/null || true)"
            record "$name" "error" "$out_rel" "${err_excerpt}" "$dur_ms" ""
            echo "  ✗ $name: error (${dur_ms}ms): ${err_excerpt}" >&2
        fi
    fi
}

echo "Running security tools → $RUN_DIR" >&2
echo "" >&2

# osv-scanner — multi-ecosystem CVE feed.
run_tool "osv-scanner" \
    "brew install osv-scanner" \
    "osv-scanner.json" \
    osv-scanner scan source --format json --recursive .

# gitleaks — secrets in git history.
run_tool "gitleaks" \
    "brew install gitleaks" \
    "gitleaks.json" \
    gitleaks detect --no-banner --report-format json --report-path "$RUN_DIR/gitleaks.json"

# semgrep — pattern-based static analysis.
run_tool "semgrep" \
    "brew install semgrep" \
    "semgrep.json" \
    semgrep scan \
        --config p/security-audit \
        --config p/owasp-top-ten \
        --json --quiet \
        --output "$RUN_DIR/semgrep.json"

# trivy — IaC + container scanning.
run_tool "trivy" \
    "brew install trivy" \
    "trivy.json" \
    trivy fs --format json --scanners vuln,misconfig,secret .

# === Add language-specific scanners below as your stack grows ===
# cargo-deny (Rust)
# pip-audit + bandit (Python)
# npm audit / yarn audit (Node)

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -n \
    --arg topic "security" \
    --arg ts "$TS" \
    --arg started "$STARTED_AT" \
    --arg completed "$COMPLETED_AT" \
    --slurpfile tools "$TOOLS_JSON" \
    '{topic: $topic, ts: $ts, started_at: $started, completed_at: $completed,
      run_dir: env.PWD, tools: $tools[0]}' > "$RUN_DIR/raw.json"

rm -f "$TOOLS_JSON"

echo "" >&2
echo "Wrote: $RUN_DIR/raw.json" >&2
echo "" >&2
echo "Next: synthesize findings with .ai/prompts/audits/security.md" >&2
echo "  (read raw.json, produce findings.md alongside it)" >&2
