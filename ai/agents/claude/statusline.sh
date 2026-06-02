#!/usr/bin/env bash
# Claude Code statusline.
#
# Reads the statusline JSON payload on stdin and prints one colorized line in
# three logical groups, separated by " · ":
#
#   <project> <branch><dirty> <ahead> [<subdir>] [<worktree>]
#       · <ctx%> <model>
#       · <5h%> <7d%>
#
# Items inside a group sit adjacent (no dot); the dim middle dot only appears
# between groups. Subdir renders only when current_dir != project_dir. Worktree
# renders only when it differs from the project basename (Claude reports the
# worktree path as project_dir, so the two are usually identical).
#
# Budget shows 5-hour and 7-day rate-limit %s on Pro/Max sessions
# (rate_limits.{five_hour,seven_day}.used_percentage); falls back to
# total cost USD when those fields are absent AND cost > 0 (API-only sessions
# with real spend; suppresses the misleading "$0.00" flash before rate limits
# populate on fresh Pro/Max sessions).
#
# Requires a Nerd Font for the glyphs. Set NO_COLOR=1 to disable ANSI colors.
#
# Schema: https://code.claude.com/docs/en/statusline.md

set -uo pipefail

input="$(cat)"

j() {
    printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null
}

# --- Nerd Font glyphs --------------------------------------------------------
G_PROJECT=''       # nf-fa-folder       U+F07B
G_BRANCH=''        # nf-dev-git_branch  U+E725
G_AHEAD=''         # nf-fa-arrow_up     U+F062
G_SUBDIR=''        # nf-fa-folder_open  U+F07C
G_WORKTREE=''      # nf-cod-repo_forked U+EBA2
G_MODEL='󰚩'         # nf-md-robot         U+F06A9
G_CTX='󰍛'           # nf-md-memory       U+F035B
G_HOUR=''          # nf-fa-clock-o      U+F017
G_WEEK=''          # nf-fa-calendar     U+F073

# --- ANSI colors (respect https://no-color.org/) -----------------------------
if [[ -z "${NO_COLOR:-}" ]]; then
    R=$'\033[0m'                       # reset
    DIM=$'\033[2m'
    GOLD=$'\033[38;2;197;160;89m'      # editorial accent
    CYAN=$'\033[38;5;39m'
    TEAL=$'\033[38;5;44m'
    BLUE=$'\033[38;5;75m'
    MAGENTA=$'\033[38;5;177m'
    GREEN=$'\033[38;5;34m'
    YELLOW=$'\033[38;5;220m'
    RED=$'\033[38;5;196m'
else
    R='' DIM='' GOLD='' CYAN='' TEAL='' BLUE='' MAGENTA='' GREEN='' YELLOW='' RED=''
fi

# Gradient by percentage: green <60, yellow 60-85, red >=85.
ramp() {
    local pct_int
    pct_int=$(printf '%.0f' "$1")
    if (( pct_int >= 85 )); then printf '%s' "$RED"
    elif (( pct_int >= 60 )); then printf '%s' "$YELLOW"
    else printf '%s' "$GREEN"
    fi
}

# --- Extract fields ----------------------------------------------------------
model=$(j '.model.display_name')
cwd=$(j '.workspace.current_dir')
project_dir=$(j '.workspace.project_dir')
project=$(basename "${project_dir:-${cwd:-?}}")
worktree=$(j '.workspace.git_worktree')
ctx_pct=$(j '.context_window.used_percentage')
five_hr=$(j '.rate_limits.five_hour.used_percentage')
seven_d=$(j '.rate_limits.seven_day.used_percentage')

# Subdir: cwd relative to project_dir, only when they differ.
# If cwd lives under a worktree directory (.claude/worktrees/<name> or
# .worktrees/<name>), peel off the worktree name and use only the path
# *below* the worktree as the subdir. This keeps the workspace label
# tight (project/<worktree>) and still exposes any deeper cwd.
subdir=""
worktree_label="${worktree:-}"
if [[ -n "$cwd" && -n "$project_dir" && "$cwd" != "$project_dir" ]]; then
    if [[ "$cwd" == "$project_dir"/* ]]; then
        subdir="${cwd#"$project_dir"/}"
    else
        subdir=$(basename "$cwd")
    fi
    if [[ "$subdir" =~ ^(\.claude/worktrees|\.worktrees)/([^/]+)(/(.*))?$ ]]; then
        worktree_label="${BASH_REMATCH[2]}"
        subdir="${BASH_REMATCH[4]:-}"
    fi
fi
# Suppress worktree label if it merely repeats the project name.
[[ "$worktree_label" == "$project" ]] && worktree_label=""

# Git: branch, dirty, ahead-of-upstream
branch=""; dirty=""; ahead_n=""
if [[ -n "$cwd" ]] && cd "$cwd" 2>/dev/null && git rev-parse --git-dir >/dev/null 2>&1; then
    branch=$(git symbolic-ref --short HEAD 2>/dev/null \
        || git rev-parse --short HEAD 2>/dev/null \
        || true)
    [[ -n "$(git status --porcelain 2>/dev/null)" ]] && dirty="*"
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
    if [[ -n "$upstream" ]]; then
        n=$(git rev-list --count "${upstream}..HEAD" 2>/dev/null || echo 0)
        [[ "$n" -gt 0 ]] && ahead_n="$n"
    fi
fi

# --- Compose -----------------------------------------------------------------
sep="${DIM} · ${R}"
out=""
join() { [[ -z "$out" ]] && out="$1" || out="${out}${sep}$1"; }

# Group 1: workspace — project[/worktree] + branch + dirty + ahead + subdir.
# Workspace context is rendered muted (DIM) so the dynamic ramp colors on
# context% / 5h% / 7d% are the things that catch the eye. The dirty marker
# stays YELLOW because it signals an action-required state.
project_label="${DIM}${G_PROJECT} ${project}${R}"
[[ -n "$worktree_label" ]] && project_label="${project_label}${DIM}/${worktree_label}${R}"

if [[ -n "$branch" ]]; then
    seg="${project_label} ${DIM}${G_BRANCH} ${branch}${R}"
    [[ -n "$dirty" ]] && seg="${seg}${YELLOW}*${R}"
    [[ -n "$ahead_n" ]] && seg="${seg} ${DIM}${G_AHEAD} ${ahead_n}${R}"
    [[ -n "$subdir" ]] && seg="${seg} ${DIM}${G_SUBDIR} ${subdir}${R}"
    join "$seg"
elif [[ -n "$project" ]]; then
    seg="${project_label}"
    [[ -n "$subdir" ]] && seg="${seg} ${DIM}${G_SUBDIR} ${subdir}${R}"
    join "$seg"
fi

# Group 2: context utilization (vivid ramp) + model (muted label).
seg=""
[[ -n "$ctx_pct" ]] && seg="$(ramp "$ctx_pct")${G_CTX} $(printf '%.0f%%' "$ctx_pct")${R}"
if [[ -n "$model" ]]; then
    if [[ -n "$seg" ]]; then
        seg="${seg} ${DIM}${G_MODEL} ${model}${R}"
    else
        seg="${DIM}${G_MODEL} ${model}${R}"
    fi
fi
[[ -n "$seg" ]] && join "$seg"

# Group 3: rate limits — 5h then 7d. Glyph + percentage carry the ramp
# color; the "5h" / "7d" window labels are muted to keep the eye on the
# value, not the unit.
seg=""
if [[ -n "$five_hr" ]]; then
    seg="$(ramp "$five_hr")${G_HOUR} $(printf '%.0f%%' "$five_hr")${R}${DIM} 5h${R}"
fi
if [[ -n "$seven_d" ]]; then
    seg2="$(ramp "$seven_d")${G_WEEK} $(printf '%.0f%%' "$seven_d")${R}${DIM} 7d${R}"
    if [[ -n "$seg" ]]; then seg="${seg} ${seg2}"; else seg="$seg2"; fi
fi
[[ -n "$seg" ]] && join "$seg"

# Cost fallback only on API-only sessions (no rate-limit fields) AND when cost
# is meaningfully > 0. Avoids the "$0.00" flash on fresh Pro/Max sessions
# before rate-limit fields populate on the first turn.
if [[ -z "$five_hr" && -z "$seven_d" ]]; then
    cost=$(j '.cost.total_cost_usd')
    if [[ -n "$cost" ]] && awk -v c="$cost" 'BEGIN { exit !(c+0 > 0) }'; then
        join "${DIM}$(printf '$%.2f' "$cost")${R}"
    fi
fi

printf '%s\n' "$out"
