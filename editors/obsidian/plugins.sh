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

PLUGIN_LOCK="$SCRIPT_DIR/plugins.lock"

verify_hash() {
    local file="$1" expected="$2" actual
    actual=$(shasum -a 256 "$file" | awk '{print $1}')
    [[ "$actual" == "$expected" ]]
}

install_plugin() {
    local id="$1" repo="$2" tag="$3" main_hash="$4" manifest_hash="$5" styles_hash="$6"
    local plugin_dir="$PLUGINS_DIR/$id"
    local installed_version=""

    if [[ -f "$plugin_dir/manifest.json" ]]; then
        installed_version=$(grep -m1 '"version"' "$plugin_dir/manifest.json" | sed 's/.*: *"//;s/".*//')
    fi
    if [[ "$installed_version" == "${tag#v}" ]]; then
        print_skip "$id"
        return 0
    fi

    local base_url="https://github.com/$repo/releases/download/$tag"
    local staging
    staging=$(mktemp -d "$PLUGINS_DIR/.${id}.XXXXXX")
    if ! curl -fsSL "$base_url/main.js" -o "$staging/main.js" \
        || ! curl -fsSL "$base_url/manifest.json" -o "$staging/manifest.json" \
        || ! verify_hash "$staging/main.js" "$main_hash" \
        || ! verify_hash "$staging/manifest.json" "$manifest_hash"; then
        rm -rf "$staging"
        print_error "Failed to verify $id ($tag)"
        return 1
    fi
    if [[ "$styles_hash" != "-" ]]; then
        if ! curl -fsSL "$base_url/styles.css" -o "$staging/styles.css" \
            || ! verify_hash "$staging/styles.css" "$styles_hash"; then
            rm -rf "$staging"
            print_error "Failed to verify $id styles ($tag)"
            return 1
        fi
    fi
    rm -rf "$plugin_dir"
    mv "$staging" "$plugin_dir"
    print_step "Installed $id ($tag)"
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

# Install plugins from GitHub releases
while IFS='|' read -r id repo tag main_hash manifest_hash styles_hash; do
    [[ -n "$id" ]] || continue
    install_plugin "$id" "$repo" "$tag" "$main_hash" "$manifest_hash" "$styles_hash"
done < "$PLUGIN_LOCK"

# Link tracked plugin configuration after installation replaces stale plugin dirs.
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
