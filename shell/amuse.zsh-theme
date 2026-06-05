# =============================================================================
# Custom ZSH Theme
# =============================================================================
# Two-line prompt. Everything on line 1 is precomputed once per prompt in a
# precmd hook (zero subshells at render time); the prompt strings just
# interpolate the cached segments.
#
#   ~/dir (main ↑2 +1 !3 ?2) [venv] wt:fix-bug cc:yolo took 8s 14:32:05
#   127 $   (yellow on success, red on failure)
#
# Line 1: dir · git (branch + ahead/behind + staged/unstaged/untracked) ·
#         venv · worktree · active Claude profile · duration (if slow) · clock
# Line 2: exit code (only on failure) + $  (yellow ok / red failed)

# Colors (modern %F{} syntax only)
CYAN="%F{51}"
PINK="%F{162}"
RED="%F{1}"
YELLOW="%F{226}"
GREEN="%F{82}"
ORANGE="%F{208}"
GOLD="%F{179}"
DIM="%F{242}"
RESET="%f"
BOLD="%B"
UNBOLD="%b"

setopt PROMPT_SUBST          # allow ${...} expansion in PROMPT each render
zmodload zsh/datetime        # $EPOCHREALTIME for command timing
autoload -Uz add-zsh-hook

# Slowest command (in seconds) that still prints nothing on the right.
: ${PROMPT_DURATION_THRESHOLD:=5}

# -----------------------------------------------------------------------------
# Segment caches (populated by _prompt_precmd, read by PROMPT/RPROMPT)
# -----------------------------------------------------------------------------
_git_segment=""
_wt_segment=""
_venv_segment=""
_profile_segment=""
_exit_segment=""
_duration_segment=""
_char_color="$YELLOW"

# -----------------------------------------------------------------------------
# Command duration
# -----------------------------------------------------------------------------
_prompt_preexec() { _cmd_start=$EPOCHREALTIME }

_fmt_duration() {
    local -i t
    (( t = $1 ))
    if   (( t < 60 ));   then printf '%ds' "$t"
    elif (( t < 3600 )); then printf '%dm%02ds' $((t / 60)) $((t % 60))
    else                      printf '%dh%02dm' $((t / 3600)) $(((t % 3600) / 60))
    fi
}

_prompt_duration_compute() {
    _duration_segment=""
    [[ -z "$_cmd_start" ]] && return
    local elapsed=$(( EPOCHREALTIME - _cmd_start ))
    unset _cmd_start
    (( elapsed >= PROMPT_DURATION_THRESHOLD )) && \
        _duration_segment="${DIM}took $(_fmt_duration "$elapsed") ${RESET}"
}

# -----------------------------------------------------------------------------
# Git: branch + ahead/behind + staged/unstaged/untracked/conflict counts.
# Single `git status --porcelain=v2 --branch` call; clean repos show just the
# branch name, matching the old minimalist look.
# -----------------------------------------------------------------------------
_prompt_git_compute() {
    _git_segment=""
    local -a lines
    lines=( "${(@f)$(command git status --porcelain=v2 --branch 2>/dev/null)}" )
    (( ${#lines} )) || return

    local head="" oid="" ab=""
    local -i ahead=0 behind=0 staged=0 unstaged=0 untracked=0 conflict=0
    local line xy
    for line in "${lines[@]}"; do
        case "$line" in
            '# branch.head '*) head="${line#\# branch.head }" ;;
            '# branch.oid '*)  oid="${line#\# branch.oid }" ;;
            '# branch.ab '*)
                ab="${line#\# branch.ab }"
                ahead="${${ab%% *}#+}"
                behind="${${ab##* }#-}"
                ;;
            ('1 '*|'2 '*)
                xy="${line[3,4]}"
                [[ "${xy[1]}" != "." ]] && (( staged++ ))
                [[ "${xy[2]}" != "." ]] && (( unstaged++ ))
                ;;
            'u '*) (( conflict++ )) ;;
            '? '*) (( untracked++ )) ;;
        esac
    done

    # Empty repo (no commits) has no branch.head value; bail if we learned nothing.
    [[ -z "$head" ]] && return

    local label
    if [[ "$head" == "(detached)" ]]; then
        label="@${oid[1,7]}"
    else
        label="$head"
    fi

    local seg="${BOLD}${GREEN}(${label}"
    (( ahead ))     && seg+=" ${CYAN}↑${ahead}"
    (( behind ))    && seg+=" ${CYAN}↓${behind}"
    (( conflict ))  && seg+=" ${RED}✗${conflict}"
    (( staged ))    && seg+=" ${GREEN}+${staged}"
    (( unstaged ))  && seg+=" ${YELLOW}!${unstaged}"
    (( untracked )) && seg+=" ${DIM}?${untracked}"
    seg+="${GREEN})${UNBOLD}${RESET} "
    _git_segment="$seg"
}

# -----------------------------------------------------------------------------
# AI / workflow context: linked git worktree + active Claude Code profile.
#   - worktree: a linked worktree's git-dir lives under .git/worktrees/<name>,
#     so git-dir != git-common-dir. Surfaces which worktree a tab is parked in.
#   - profile: $CLAUDE_PROFILE is read by the `cc` shell function; when you've
#     pinned a tab to a non-default profile, show it (yolo highlighted red).
# -----------------------------------------------------------------------------
_prompt_context_compute() {
    _wt_segment=""
    _profile_segment=""

    local -a rp
    rp=( "${(@f)$(command git rev-parse --git-dir --git-common-dir 2>/dev/null)}" )
    if (( ${#rp} == 2 )) && [[ "${rp[1]:A}" != "${rp[2]:A}" ]]; then
        _wt_segment="${CYAN}wt:${rp[1]:t}${RESET} "
    fi

    if [[ -n "$CLAUDE_PROFILE" ]]; then
        local pc="$DIM"
        case "$CLAUDE_PROFILE" in
            yolo)  pc="$RED" ;;
            scout) pc="$CYAN" ;;
            dev)   pc="$GREEN" ;;
        esac
        _profile_segment="${pc}cc:${CLAUDE_PROFILE}${RESET} "
    fi
}

# Python virtualenv indicator
_prompt_venv_compute() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        _venv_segment="${GOLD}[${VIRTUAL_ENV:t}]${RESET} "
    else
        _venv_segment=""
    fi
}

# -----------------------------------------------------------------------------
# precmd: capture exit status FIRST (before any arithmetic clobbers $?), then
# refresh every cached segment.
# -----------------------------------------------------------------------------
_prompt_precmd() {
    local -i last_exit=$?
    if (( last_exit )); then
        _exit_segment="${RED}${last_exit}${RESET} "
        _char_color="$RED"
    else
        _exit_segment=""
        _char_color="$YELLOW"
    fi
    _prompt_duration_compute
    _prompt_git_compute
    _prompt_context_compute
    _prompt_venv_compute
}

add-zsh-hook preexec _prompt_preexec
add-zsh-hook precmd  _prompt_precmd

# -----------------------------------------------------------------------------
# Prompt (pure interpolation — no subshells at render time). Everything,
# including duration + clock, lives on line 1's left; no right prompt.
# -----------------------------------------------------------------------------
PROMPT='
${BOLD}${PINK}%~${UNBOLD}${RESET} ${_git_segment}${_venv_segment}${_wt_segment}${_profile_segment}${_duration_segment}${DIM}%*${RESET}
${_exit_segment}${_char_color}\$${RESET} '
