#!/usr/bin/env bash
# assess.sh — run an independent, adversarial code-health/design assessment.
#
# Routes the work past a DIFFERENT model (default: Claude Fable 5) acting as a
# skeptical principal engineer, read-only, whose job is to find what the author
# and their default agent are blind to. This is the structural counter to model
# sycophancy: a fresh-context critic with no stake in the work, not a prompt
# asking the same model to "be harsher."
#
# Its findings are CLAIMS TO VERIFY, not gospel — verify before acting (the skill
# body, SKILL.md, carries that discipline).
#
# Usage:
#   assess.sh [--model <id>] [--scope <path>] [--out <dir>] [--budget <usd>] [focus text...]
#
#   assess.sh                                  # broad repo assessment
#   assess.sh security of the agent hooks      # focused assessment
#   assess.sh --scope cli/src/dotfiles/cmd/agent  the agent subsystem
#   assess.sh --model claude-opus-4-8 ...      # cheaper assessor
#
# Requires the `claude` CLI on PATH (the assessor is invoked via `claude -p`).

set -eo pipefail

MODEL="claude-fable-5"
SCOPE=""
OUT=""
BUDGET="2.00"
focus=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --scope) SCOPE="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --budget) BUDGET="$2"; shift 2 ;;
        --) shift; focus+=("$@"); break ;;
        *) focus+=("$1"); shift ;;
    esac
done

if ! command -v claude >/dev/null 2>&1; then
    echo "assess: the 'claude' CLI is not on PATH (the assessor runs via 'claude -p')." >&2
    exit 1
fi

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
SCOPE="${SCOPE:-$repo_root}"
OUT="${OUT:-$repo_root/docs/health/assessments}"
focus_text="${focus[*]}"
[[ -z "$focus_text" ]] && focus_text="overall code health, design, and feature completeness"

slug=$(printf '%s' "$focus_text" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-' | cut -c1-40)
[[ -z "$slug" ]] && slug="repo"
stamp=$(date +%Y-%m-%d)
mkdir -p "$OUT"
report="$OUT/assessment-$stamp-$slug.md"

prompt="You are $MODEL acting as a skeptical, INDEPENDENT principal engineer doing an
ADVERSARIAL assessment of: $SCOPE

Focus: $focus_text

You are NOT the author and have no stake in this work. Your job is to find what
the author and their default coding agent are most likely BLIND to — the issues
a grumpy 15-year principal would still flag. Be direct, rank by leverage, cite
file paths and line numbers. NO flattery, no praise padding, no hedging.

Read for context first (read-only — do NOT edit anything): the repo's top-level
docs (README, ENGINEERING.md / CANON-style philosophy, AGENTS.md), any
docs/health/ ledger or prior assessment, then sample widely across the scope by
churn and risk. Verify each claim against the actual source before reporting it.

Deliver four ranked sections, concrete and skeptical:
1. CODE HEALTH — the highest-leverage issues a strong reviewer still flags, with
   emphasis on what the existing gates (linters, type-checkers, tests, ratchets)
   STRUCTURALLY cannot catch: wrong abstractions, hidden coupling, weak module
   boundaries, primitive obsession, tests that assert implementation not
   behavior, non-hermetic tests. file:line + why + the fix.
2. RISK & CORRECTNESS — latent crash/failure modes, unhandled edge cases,
   security or data-safety gaps, and anything that only works on the author's
   machine. Be specific about the trigger.
3. FEATURE / CAPABILITY COMPLETENESS — what is half-built (finish or kill), what
   is over-built (YAGNI to cut), and what is genuinely missing.
4. WHAT TO ADD / ALTER / CUT — concrete proposals; for each give the argument
   FOR, the strongest argument AGAINST, and your verdict. Be willing to say
   'cut this' and 'do not build that'.

End with the 3 things you would do FIRST and the single biggest risk. Be concise
but information-dense. No filler."

echo "assess: running $MODEL over $SCOPE (focus: $focus_text)…" >&2
echo "assess: budget cap \$$BUDGET; this calls a paid model and may take a few minutes." >&2

{
    printf '# Adversarial Assessment — %s\n\n' "$focus_text"
    printf '> Independent adversarial review by **%s** (read-only), %s.\n' "$MODEL" "$stamp"
    printf '> Scope: `%s`\n>\n' "$SCOPE"
    printf '> **Findings are claims to verify, not gospel.** Verify each against\n'
    printf '> source before acting — that discipline is the point (it is your check\n'
    printf '> against your own agreeableness). See ai/skills/adversarial-assessor.\n\n'
    printf -- '---\n\n'
    # Read-only via an allow-list (Read/Grep/Glob) rather than --permission-mode
    # plan: plan mode diverts the substantive output into a plan file and leaves
    # only a closing remark on stdout. The allow-list keeps the assessor unable to
    # edit while its full report comes back on stdout where we capture it.
    claude -p --model "$MODEL" --max-budget-usd "$BUDGET" \
        --allowedTools Read Grep Glob \
        --append-system-prompt "Stay strictly read-only. Be adversarial, specific, and cite file paths. No flattery." \
        -- "$prompt"
} >"$report"

echo "assess: report written → $report" >&2
echo "$report"
