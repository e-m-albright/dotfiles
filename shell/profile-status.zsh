# shellcheck shell=bash
# Compact, local-only summary of the active host profile.

profile_status() {
    local detail="${1:-medium}"
    local profile="${DOTFILES_PROFILE:-personal}"

    case "$detail" in
        off) return 0 ;;
        short)
            printf 'dotfiles: %s profile · profile_status medium|long for details\n' "$profile"
            return 0
            ;;
        medium | long) ;;
        *)
            printf 'profile_status: expected short, medium, long, or off\n' >&2
            return 2
            ;;
    esac

    printf 'dotfiles profile: %s\n' "$profile"
    printf '  shell: shared zsh configuration; Homebrew analytics disabled\n'
    if [[ "$profile" == "work" ]]; then
        printf '  agents: Claude Code and Pi; no personal connectors or local models\n'
        printf '  data: agent prompts and selected code go to the authenticated model provider\n'
    else
        printf '  agents: Workbench-managed personal configuration\n'
    fi
    printf '  runtimes: Node via fnm; Python via uv; Terraform via tenv\n'

    if [[ "$detail" == "long" ]]; then
        local tool location
        for tool in brew fnm node uv python3.14 tenv terraform claude pi; do
            location=$(command -v "$tool" 2>/dev/null || true)
            if [[ -n "$location" ]]; then
                location=${location/#$HOME/~}
                printf '  %-10s %s\n' "$tool" "$location"
            else
                printf '  %-10s unavailable\n' "$tool"
            fi
        done
        printf '  config: %s\n' "${DOTFILES_DIR:-$HOME/code/public/dotfiles}"
    fi
}

_dotfiles_startup_detail="${DOTFILES_STARTUP_DETAIL:-}"
if [[ -z "$_dotfiles_startup_detail" ]]; then
    [[ "${DOTFILES_PROFILE:-personal}" == "work" ]] && _dotfiles_startup_detail=short \
        || _dotfiles_startup_detail=off
fi
profile_status "$_dotfiles_startup_detail"
unset _dotfiles_startup_detail
