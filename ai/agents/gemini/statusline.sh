#!/usr/bin/env bash
# Antigravity/agy statusline, shaped to match Pi as closely as agy's custom
# command surface allows:
#
#   agy <cwd> (<branch> [!n] [+n] [*n] [?n] [⇡n] [⇣n]) · ctx: n% · Fast off · <model>
#
# agy passes StatusLineData JSON on stdin. The payload is not public, so this
# accepts multiple observed/likely field names and degrades gracefully.

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

    local branch counts staged unstaged untracked conflicts ahead=0 behind=0 upstream_counts parts=()
    branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || printf 'detached')
    counts=$(git status --porcelain 2>/dev/null | count_git_porcelain)
    read -r staged unstaged untracked conflicts <<< "$counts"
    upstream_counts=$(git rev-list --left-right --count 'HEAD...@{u}' 2>/dev/null || true)
    if [[ -n "$upstream_counts" ]]; then
        read -r ahead behind <<< "$upstream_counts"
    fi

    parts+=("$branch")
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

cwd=$(j '.workspace.current_dir // .workspace.cwd // .workspace.path // .cwd // .current_dir // .project.path')
model=$(j '.model.display_name // .model.name // .modelInfo.displayName // .modelInfo.name // .model // .agent.model')
ctx_pct=$(j '.context.used_percentage // .context_window.used_percentage // .context.percent_used // .currentUsage.contextPercent // .currentUsage.context_used_percent // .contextUsedPercent')
fast=$(printf '%s' "$input" | jq -r '
    if .agent and (.agent | has("fast_mode")) then .agent.fast_mode
    elif has("fast_mode") then .fast_mode
    elif .mode and (.mode | has("fast")) then .mode.fast
    elif has("fastMode") then .fastMode
    else empty end
' 2>/dev/null)

sep="${DIM} · ${R}"
out="${NOTE}agy${R} ${DIM}$(short_path "${cwd:-?}")${R}"
git_text=$(git_segment "$cwd")
[[ -n "$git_text" ]] && out="${out} ${git_text}"

if [[ -n "$ctx_pct" ]]; then
    out="${out}${sep}$(ramp "$ctx_pct")ctx: $(printf '%.0f%%' "$ctx_pct")${R}"
fi
case "$(printf '%s' "$fast" | tr '[:upper:]' '[:lower:]')" in
    true|1|on|yes|fast) out="${out}${sep}${WARN}Fast on${R}" ;;
    false|0|off|no) out="${out}${sep}${DIM}Fast off${R}" ;;
esac
if [[ -n "$model" ]]; then
    out="${out}${sep}${DIM}${model}${R}"
fi

printf '%s\n' "$out"
