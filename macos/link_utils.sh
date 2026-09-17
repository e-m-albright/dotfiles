#!/usr/bin/env bash

# Replace one managed symlink without destroying an unmanaged file or directory.
# Requires print_step/print_skip/print_warn from print_utils.sh.
safe_link() {
    local src="$1" dest="$2"
    local name backup stamp
    name="$(basename "$dest")"

    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$src" ]]; then
        print_skip "$name"
        return 0
    fi

    mkdir -p "$(dirname "$dest")"
    if [[ -e "$dest" || -L "$dest" ]]; then
        stamp="$(date '+%Y%m%d-%H%M%S')"
        backup="${dest}.backup-${stamp}"
        while [[ -e "$backup" || -L "$backup" ]]; do
            backup="${backup}-next"
        done
        mv "$dest" "$backup"
        print_warn "Preserved existing $name as $(basename "$backup")"
    fi

    ln -s "$src" "$dest"
    print_step "Linked $name"
}
