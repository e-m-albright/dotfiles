#!/usr/bin/env bash
# Direct-append agent-activity hook. Kept dead-simple (no Python boot) so it is
# cheap to run on every agent turn. Schema is enforced by
# cli/tests/test_ledger_hook_schema.py against core LedgerEntry.
set -eo pipefail

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles"
ledger="$state_dir/ledger.jsonl"
mkdir -p "$state_dir"

ts="$(date -u +%Y-%m-%dT%H:%M:%S)"
session_id="${LEDGER_SESSION:-${CLAUDE_SESSION_ID:-unknown}}"
vendor="${LEDGER_VENDOR:-claude}"
cwd="$PWD"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
task="${LEDGER_TASK:-}"
status="${LEDGER_STATUS:-active}"

# JSON-encode a string value (handles quotes, backslashes, control chars).
esc() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()), end="")'; }

ts_json="$(esc "$ts")"
sid_json="$(esc "$session_id")"
vendor_json="$(esc "$vendor")"
cwd_json="$(esc "$cwd")"
branch_json="$(esc "$branch")"
task_json="$(esc "$task")"
status_json="$(esc "$status")"

printf '{"ts":%s,"session_id":%s,"vendor":%s,"cwd":%s,"branch":%s,"task":%s,"status":%s}\n' \
  "$ts_json" "$sid_json" "$vendor_json" "$cwd_json" \
  "$branch_json" "$task_json" "$status_json" \
  >> "$ledger"
