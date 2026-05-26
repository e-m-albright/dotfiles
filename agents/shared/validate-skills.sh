#!/usr/bin/env bash
# shellcheck disable=SC2059
# (Project convention: printf format strings include color escapes; matches bin/dotfiles style.)
#
# Validate skill and agent files against the conventions in
# .ai/rules/process/skill-format.mdc and .ai/rules/process/agent-format.mdc.
#
# Checks (per file):
#   name == dirname (skills) / name == filename-without-ext (agents)
#   frontmatter present and well-formed
#   description present, contains "Use when", <= 1024 chars
#   body <= 500 lines (skills); <= 200 lines (agents)
#   no spec violations (caps-rule, missing trigger, etc.)
#
# Exit 0 if all pass. Exit 1 if any FAIL. Warnings don't fail the run.

set -eo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

FAIL_COUNT=0
WARN_COUNT=0
PASS_COUNT=0

# Extract a single-line frontmatter value. Returns empty if not present.
# Usage: get_frontmatter <file> <key>
get_frontmatter() {
    awk -v key="$2" '
        /^---$/ { c++; next }
        c == 1 {
            prefix = key ": "
            if (index($0, prefix) == 1) {
                sub("^" prefix, "")
                print
                exit
            }
        }
    ' "$1"
}

# Count body lines (excluding YAML frontmatter).
body_line_count() {
    awk 'BEGIN{in_fm=0; printed_lines=0} /^---$/{if(in_fm==0){in_fm=1;next}else{in_fm=2;next}} in_fm==2{printed_lines++} END{print printed_lines}' "$1"
}

# Check one file. Args: <kind> <file> <expected_name>.
check_file() {
    local kind="$1" file="$2" expected_name="$3"
    local rel="${file#"$DOTFILES_DIR"/}"
    local errors=() warnings=()

    # Frontmatter present?
    if ! head -1 "$file" | grep -qE '^---$'; then
        printf "${RED}FAIL${NC} %s\n  missing frontmatter\n" "$rel"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return
    fi

    local name desc
    name=$(get_frontmatter "$file" 'name')
    desc=$(get_frontmatter "$file" 'description')

    # Name == dirname/filename
    if [[ "$name" != "$expected_name" ]]; then
        errors+=("name '$name' != expected '$expected_name'")
    fi

    # Name regex
    if ! [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
        errors+=("name '$name' violates [a-z0-9-] (no consec/leading/trailing hyphens)")
    fi

    # Description present
    if [[ -z "$desc" ]]; then
        errors+=("missing description")
    else
        # Length
        if (( ${#desc} > 1024 )); then
            errors+=("description ${#desc} chars > 1024")
        elif (( ${#desc} < 20 )); then
            warnings+=("description ${#desc} chars < 20 (EMPTY_DESCRIPTION)")
        fi

        # Use-when trigger
        if ! echo "$desc" | grep -qiE '\b[Uu]se when\b|\b[Tt]rigger when\b'; then
            warnings+=("description lacks 'Use when' trigger clause (MISSING_TRIGGER)")
        fi
    fi

    # Body length
    local body_lines limit
    body_lines=$(body_line_count "$file")
    if [[ "$kind" == "skill" ]]; then
        limit=500
    else
        limit=200
    fi
    if (( body_lines > limit )); then
        warnings+=("body $body_lines lines > $limit ($kind cap)")
    fi

    # Caps-rule (OVER_CONSTRAINED): count standalone MUST/ALWAYS/NEVER in body
    local caps_count
    caps_count=$(awk '
        BEGIN { in_fm = 0; n = 0 }
        /^---$/ { if (in_fm == 0) { in_fm = 1; next } else { in_fm = 2; next } }
        in_fm == 2 {
            while (match($0, /(MUST|ALWAYS|NEVER)/)) {
                pre = (RSTART == 1) ? "" : substr($0, RSTART - 1, 1)
                post = substr($0, RSTART + RLENGTH, 1)
                if (pre !~ /[A-Za-z0-9_]/ && post !~ /[A-Za-z0-9_]/) n++
                $0 = substr($0, RSTART + RLENGTH)
            }
        }
        END { print n }
    ' "$file")
    if (( caps_count > 15 )); then
        warnings+=("$caps_count instances of MUST/ALWAYS/NEVER in caps (OVER_CONSTRAINED, threshold 15)")
    fi

    # Print result
    if (( ${#errors[@]} > 0 )); then
        printf "${RED}FAIL${NC} %s\n" "$rel"
        for e in "${errors[@]}"; do printf "  ${RED}✗${NC} %s\n" "$e"; done
        for w in "${warnings[@]}"; do printf "  ${YELLOW}⚠${NC} %s\n" "$w"; done
        FAIL_COUNT=$((FAIL_COUNT + 1))
    elif (( ${#warnings[@]} > 0 )); then
        printf "${YELLOW}WARN${NC} %s\n" "$rel"
        for w in "${warnings[@]}"; do printf "  ${YELLOW}⚠${NC} %s\n" "$w"; done
        WARN_COUNT=$((WARN_COUNT + 1))
    else
        printf "${GREEN}OK${NC}   %s ${DIM}(%d-line body)${NC}\n" "$rel" "$body_lines"
        PASS_COUNT=$((PASS_COUNT + 1))
    fi
}

printf "${BLUE}Validating skills (.ai/skills/)${NC}\n"
for skill_dir in "$DOTFILES_DIR"/.ai/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    local_name=$(basename "$skill_dir")
    skill_md="${skill_dir%/}/SKILL.md"
    if [[ ! -f "$skill_md" ]]; then
        printf "${RED}FAIL${NC} %s — missing SKILL.md\n" "${skill_dir#"$DOTFILES_DIR"/}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi
    check_file skill "$skill_md" "$local_name"
done

printf "\n${BLUE}Validating agents (.ai/agents/)${NC}\n"
if [[ -d "$DOTFILES_DIR/.ai/agents" ]]; then
    for agent_md in "$DOTFILES_DIR"/.ai/agents/*.md; do
        [[ -f "$agent_md" ]] || continue
        expected_name=$(basename "$agent_md" .md)
        check_file agent "$agent_md" "$expected_name"
    done
fi

printf "\n"
printf "${BLUE}Summary${NC}\n"
printf "  ${GREEN}%d passed${NC}\n" "$PASS_COUNT"
(( WARN_COUNT > 0 )) && printf "  ${YELLOW}%d with warnings${NC}\n" "$WARN_COUNT"
(( FAIL_COUNT > 0 )) && printf "  ${RED}%d failed${NC}\n" "$FAIL_COUNT"

if (( FAIL_COUNT > 0 )); then
    exit 1
fi
exit 0
