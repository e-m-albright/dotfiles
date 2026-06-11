#!/usr/bin/env bash
# Claude Code statusline, shaped to match Pi as closely as Claude's one-line
# command surface allows:
#
#   claude <cwd> (<branch> [wt:name] [!n] [+n] [*n] [?n] [⇡n] [⇣n]) · ctx: n% · 5h: n% used · 7d: n% used · <model>
#
# Reads Claude's statusline JSON payload on stdin. Set NO_COLOR=1 to disable
# ANSI colors. Schema: https://code.claude.com/docs/en/statusline.md

set -uo pipefail

input="$(cat)"

j() {
    printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null
}

if [[ -z "${NO_COLOR:-}" ]]; then
    R=$'\033[0m'
    DIM=$'\033[2m'
    NOTE=$'\033[38;2;128;166;173m'
    WARN=$'\033[38;2;217;145;61m'
    DANGER=$'\033[38;2;217;120;77m'
    AMBER_HOT=$'\033[38;2;217;120;77m'
    AMBER=$'\033[38;2;217;145;61m'
    GOLD=$'\033[38;2;211;177;95m'
    SAGE=$'\033[38;2;143;168;121m'
else
    R='' DIM='' NOTE='' WARN='' DANGER='' AMBER_HOT='' AMBER='' GOLD='' SAGE=''
fi

ramp() {
    local pct_int
    pct_int=$(printf '%.0f' "${1:-0}")
    if   (( pct_int >= 90 )); then printf '%s' "$AMBER_HOT"
    elif (( pct_int >= 75 )); then printf '%s' "$AMBER"
    elif (( pct_int >= 55 )); then printf '%s' "$GOLD"
    else printf '%s' "$SAGE"
    fi
}

home="${HOME:-}"
short_path() {
    local path="$1"
    if [[ -n "$home" && "$path" == "$home"* ]]; then
        printf '~%s' "${path#"$home"}"
    else
        printf '%s' "$path"
    fi
}

count_git_porcelain() {
    local staged=0 unstaged=0 untracked=0 conflicts=0 line status index worktree
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        status="${line:0:2}"
        index="${status:0:1}"
        worktree="${status:1:1}"
        if [[ "$status" == "??" ]]; then
            untracked=$((untracked + 1))
            continue
        fi
        case "$status" in
            DD|AU|UD|UA|DU|AA|UU) conflicts=$((conflicts + 1)); continue ;;
        esac
        [[ -n "$index" && "$index" != " " && "$index" != "?" ]] && staged=$((staged + 1))
        [[ -n "$worktree" && "$worktree" != " " && "$worktree" != "?" ]] && unstaged=$((unstaged + 1))
    done
    printf '%s %s %s %s' "$staged" "$unstaged" "$untracked" "$conflicts"
}

git_segment() {
    local cwd="$1"
    [[ -z "$cwd" ]] && return 0
    cd "$cwd" 2>/dev/null || return 0
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0

    local branch git_dir common_dir top_level worktree_name counts staged unstaged untracked conflicts ahead=0 behind=0 upstream_counts parts=()
    branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || printf 'detached')
    git_dir=$(git rev-parse --path-format=absolute --git-dir 2>/dev/null || true)
    common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
    top_level=$(git rev-parse --show-toplevel 2>/dev/null || true)
    if [[ -n "$git_dir" && -n "$common_dir" && "$git_dir" != "$common_dir" && -n "$top_level" ]]; then
        worktree_name=$(basename "$top_level")
    fi

    counts=$(git status --porcelain 2>/dev/null | count_git_porcelain)
    read -r staged unstaged untracked conflicts <<< "$counts"
    upstream_counts=$(git rev-list --left-right --count 'HEAD...@{u}' 2>/dev/null || true)
    if [[ -n "$upstream_counts" ]]; then
        read -r ahead behind <<< "$upstream_counts"
    fi

    parts+=("$branch")
    [[ -n "${worktree_name:-}" ]] && parts+=("${NOTE}wt:${worktree_name}${R}")
    (( conflicts > 0 )) && parts+=("${DANGER}!${conflicts}${R}")
    (( staged > 0 )) && parts+=("${WARN}+${staged}${R}")
    (( unstaged > 0 )) && parts+=("${WARN}*${unstaged}${R}")
    (( untracked > 0 )) && parts+=("${WARN}?${untracked}${R}")
    (( ahead > 0 )) && parts+=("${NOTE}⇡${ahead}${R}")
    (( behind > 0 )) && parts+=("${WARN}⇣${behind}${R}")
    if (( ${#parts[@]} == 1 )); then
        parts+=("${SAGE}✓${R}")
    fi

    local IFS=' '
    printf '%s%s%s' "${DIM}(" "${parts[*]}" ")${R}"
}

model=$(j '.model.display_name')
cwd=$(j '.workspace.current_dir')
ctx_pct=$(j '.context_window.used_percentage')
five_used=$(j '.rate_limits.five_hour.used_percentage')
seven_used=$(j '.rate_limits.seven_day.used_percentage')

sep="${DIM} · ${R}"
out="${NOTE}claude${R} ${DIM}$(short_path "${cwd:-?}")${R}"
git_text=$(git_segment "$cwd")
[[ -n "$git_text" ]] && out="${out} ${git_text}"

if [[ -n "$ctx_pct" ]]; then
    out="${out}${sep}$(ramp "$ctx_pct")ctx: $(printf '%.0f%%' "$ctx_pct")${R}"
fi
if [[ -n "$five_used" ]]; then
    out="${out}${sep}$(ramp "$five_used")5h: $(printf '%.0f%%' "$five_used") used${R}"
fi
if [[ -n "$seven_used" ]]; then
    out="${out}${sep}$(ramp "$seven_used")7d: $(printf '%.0f%%' "$seven_used") used${R}"
fi
if [[ -n "$model" ]]; then
    out="${out}${sep}${DIM}${model}${R}"
fi

printf '%s\n' "$out"
