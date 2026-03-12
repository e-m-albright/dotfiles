#!/bin/bash
set -eo pipefail

# Obsidian community plugin installer
# Downloads plugins from GitHub releases into the vault's .obsidian/plugins/ directory.
# Usage: ./plugins.sh [vault_path]

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
source "$DOTFILES_DIR/macos/print_utils.sh"

VAULT="${1:-$HOME/code/private/notes}"
PLUGINS_DIR="$VAULT/.obsidian/plugins"

# Plugin registry: "id|github_repo" per line
# Add new plugins here. Run `dotfiles install` or `./plugins.sh` to install.
PLUGIN_LIST=(
    # ── Study & Retention ──────────────────────────────────────────────────────
    "obsidian-spaced-repetition|st3v3nmw/obsidian-spaced-repetition"

    # ── Power Tools ────────────────────────────────────────────────────────────
    "dataview|blacksmithgu/obsidian-dataview"
    "templater-obsidian|SilentVoid13/Templater"
    "calendar|liamcain/obsidian-calendar-plugin"
    "nldates-obsidian|argenos/nldates-obsidian"
    "obsidian-linter|platers/obsidian-linter"
)

install_plugin() {
    local id="$1" repo="$2"
    local plugin_dir="$PLUGINS_DIR/$id"

    # Skip if already installed (has main.js)
    if [[ -f "$plugin_dir/main.js" ]]; then
        print_skip "$id"
        return 0
    fi

    mkdir -p "$plugin_dir"

    # Fetch latest release tag
    local release_url="https://api.github.com/repos/$repo/releases/latest"
    local tag
    tag=$(curl -fsSL "$release_url" 2>/dev/null | grep '"tag_name"' | head -1 | sed 's/.*: "//;s/".*//')

    if [[ -z "$tag" ]]; then
        print_warn "Could not fetch latest release for $id ($repo)"
        rm -rf "$plugin_dir"
        return 1
    fi

    local base_url="https://github.com/$repo/releases/download/$tag"
    local ok=true

    for file in main.js manifest.json; do
        if ! curl -fsSL "$base_url/$file" -o "$plugin_dir/$file" 2>/dev/null; then
            print_warn "Failed to download $file for $id"
            ok=false
        fi
    done

    # styles.css is optional
    curl -fsSL "$base_url/styles.css" -o "$plugin_dir/styles.css" 2>/dev/null || true

    if $ok; then
        print_step "Installed $id ($tag)"
    else
        rm -rf "$plugin_dir"
        print_error "Failed to install $id"
        return 1
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────

if [[ ! -d "$VAULT/.obsidian" ]]; then
    print_warn "Obsidian vault not found at $VAULT"
    exit 1
fi

mkdir -p "$PLUGINS_DIR"

# Symlink community-plugins.json (enables the plugins in Obsidian)
local_community="$SCRIPT_DIR/community-plugins.json"
vault_community="$VAULT/.obsidian/community-plugins.json"
if [[ -L "$vault_community" ]] && [[ "$(readlink "$vault_community")" == "$local_community" ]]; then
    print_skip "community-plugins.json"
else
    ln -sf "$local_community" "$vault_community"
    print_step "Linked community-plugins.json"
fi

# Symlink plugin configs (data.json for each plugin that has one)
if [[ -d "$SCRIPT_DIR/plugin-configs" ]]; then
    for config_file in "$SCRIPT_DIR/plugin-configs"/*.json; do
        [[ -f "$config_file" ]] || continue
        local_id="$(basename "$config_file" .json)"
        config_dest="$PLUGINS_DIR/$local_id/data.json"
        mkdir -p "$PLUGINS_DIR/$local_id"
        if [[ -L "$config_dest" ]] && [[ "$(readlink "$config_dest")" == "$config_file" ]]; then
            print_skip "$local_id config"
        else
            ln -sf "$config_file" "$config_dest"
            print_step "Linked $local_id config"
        fi
    done
fi

# Install plugins from GitHub releases
for entry in "${PLUGIN_LIST[@]}"; do
    id="${entry%%|*}"
    repo="${entry##*|}"
    install_plugin "$id" "$repo"
done
