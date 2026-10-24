#!/bin/bash
# Shared host configuration inventory. Callers own error handling and output.

resolve_host_profile() {
    PROFILE="${1:-}"
    if [[ -z "$PROFILE" ]]; then
        PROFILE="${DOTFILES_PROFILE-personal}"
        if [[ -f "$HOME/.config/dotfiles/profile" ]]; then
            PROFILE="$(< "$HOME/.config/dotfiles/profile")"
        fi
    fi
    if [[ "$PROFILE" != personal && "$PROFILE" != work ]]; then
        printf 'Invalid host profile: %s; expected personal or work\n' "$PROFILE" >&2
        return 2
    fi
}

host_tool_available() {
    case "$1" in
        -) return 0 ;;
        app:Ghostty) command -v ghostty >/dev/null 2>&1 || [[ -d /Applications/Ghostty.app ]] ;;
        app:*) [[ -d "/Applications/${1#app:}.app" ]] ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
    esac
}

# Every TSV field is nonempty; '-' marks links without a tool prerequisite.
link_host_configuration() {
    local phase="$1" profiles label source destination required_tool
    while IFS=$'\t' read -r profiles label source destination required_tool; do
        [[ -z "$profiles" || "$profiles" == \#* ]] && continue
        [[ ",$profiles," == *",$PROFILE,"* ]] || continue
        if [[ "$phase" == shell && "$required_tool" != - ]]; then continue; fi
        if [[ "$phase" == tools && "$required_tool" == - ]]; then continue; fi
        if host_tool_available "$required_tool"; then
            mkdir -p "$(dirname "$HOME/$destination")"
            safe_link "$DOTFILES_DIR/$source" "$HOME/$destination"
            print_success "$label configured"
        fi
    done < "$DOTFILES_DIR/config/links.tsv"
}

write_host_markers() {
    mkdir -p "$HOME/.config/dotfiles"
    printf '%s\n' "$PROFILE" > "$HOME/.config/dotfiles/profile"
    printf '%s\n' "$DOTFILES_DIR" > "$HOME/.config/dotfiles/root"
}
