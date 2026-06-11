#!/usr/bin/env bash
#
# verify-before-done — a Stop hook that enforces kernel article K1
# ("verify before claiming done: evidence before assertions").
#
# When the agent ends a turn asserting that something passes / works / is verified
# but ran NO tools that turn to actually check, this blocks once with a nudge to
# show the evidence or soften the claim. It is the deterministic counter to the
# model's trained tendency to declare success it didn't observe.
#
# Conservative by construction — three guards keep false-blocks rare:
#   1. only STRONG verification phrases (ai/agents/shared/verify-claims.txt) trip it;
#   2. if the agent ran any tool this turn, the claim is trusted (allow);
#   3. stop_hook_active caps it at a single nudge per turn — it can never loop.
# Anything it can't parse, it fails OPEN (exit 0): a missed lie beats a false block.
#
# Contract — Claude Code Stop / SubagentStop hook. The jq parser below assumes the
# Claude Code transcript schema (.type "user"/"assistant", .message.content[] with
# tool_use / tool_result blocks). It is deliberately NOT wired to Codex: that
# rollout JSONL is a different, unverified shape, and a hook that silently fails
# open on an unverified contract is the exact unproven claim this hook polices.
#   stdin  = {"transcript_path": "...", "stop_hook_active": bool, ...}
#   block  = print {"decision":"block","reason":"..."} to stdout, exit 0
#   allow  = no output, exit 0

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAIMS_FILE="${VERIFY_CLAIMS_FILE:-$SCRIPT_DIR/../verify-claims.txt}"

# jq parses the transcript; without it we can't reason, so allow.
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"

# Already re-prompted by a prior stop hook → don't nudge twice (loop guard).
[ "$(jq -r '.stop_hook_active // false' <<<"$input" 2>/dev/null)" = "true" ] && exit 0

transcript="$(jq -r '.transcript_path // empty' <<<"$input" 2>/dev/null)"
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0
[ -f "$CLAIMS_FILE" ] || exit 0

# Parse the current turn (everything after the last human message): how many tool
# calls the assistant made, and the text of its final message. Tab-separated:
# "<tool_count>\t<final assistant text>". Bounded to the tail for speed.
parsed="$(tail -n 500 "$transcript" | jq -rs '
  def is_human:
    .type == "user"
    and ((.message.content // []) as $c
         | if ($c | type) == "string" then true
           else ($c | map(.type) | index("tool_result") | not) end);
  . as $all
  | ([range(0; length) | select($all[.] | is_human)] | last // -1) as $start
  | $all[($start + 1):] as $turn
  | ($turn | map((.message.content // []) | map(select(.type == "tool_use")))
           | flatten | length) as $tools
  | ($turn | map(select(.type == "assistant")) | last // null
           | (.message.content // []) | map(select(.type == "text") | .text)
           | join("\n")) as $text
  | "\($tools)\t\($text // "")"
' 2>/dev/null)" || exit 0

[ -n "$parsed" ] || exit 0
tools="${parsed%%$'\t'*}"
text="${parsed#*$'\t'}"

# Non-numeric tool count means a parse glitch — fail open.
[[ "$tools" =~ ^[0-9]+$ ]] || exit 0

# No strong verification claim in the final message → nothing to enforce.
# Strip '#' comments and blank lines first (grep -f would treat them as patterns —
# a commented-out paren would crash the match and fail open silently).
printf '%s' "$text" | grep -iqEf <(grep -vE '^[[:space:]]*(#|$)' "$CLAIMS_FILE") || exit 0

# Claim present, but the agent ran tools this turn → trust it.
[ "$tools" -gt 0 ] && exit 0

# Claim present with zero tools this turn → block once with a nudge.
#
# Telemetry: record every block so the gate's firing is OBSERVABLE — otherwise its
# value (and the claim patterns) rest on intuition, and an unfired gate is itself an
# unverified done-claim. Append-only, best-effort; opt out with VERIFY_LOG=/dev/null.
log="${VERIFY_LOG:-$HOME/.claude/verify-before-done.log}"
if [ "$log" != "/dev/null" ] && mkdir -p "$(dirname "$log")" 2>/dev/null; then
    printf '%s\tblock\t%s\n' "$(date -u +%FT%TZ)" "$(printf '%s' "$text" | tr '\n\t' '  ' | cut -c1-100)" >>"$log" 2>/dev/null || true
fi

reason="K1 — verify before claiming done. Your reply asserts something passes/works/is verified, but you ran no tools this turn to check it. Run the test/build/command and cite the actual result, or soften the claim to what you actually observed."
jq -cn --arg r "$reason" '{decision: "block", reason: $r}'
exit 0
