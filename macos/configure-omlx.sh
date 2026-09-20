#!/usr/bin/env bash
set -euo pipefail

formula="jundot/omlx/omlx"
model_repo="Jundot/Qwen3.6-35B-A3B-oQ4e-mtp"
model_revision="14c285372cbdb1777adea5bb49087ced0bffc0b5"
model_dir="$HOME/.omlx/models/$model_repo"
model_revision_file="$model_dir/.dotfiles-revision"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
settings_overlay="$script_dir/omlx/settings.json"
settings_file="$HOME/.omlx/settings.json"
restart_required="$HOME/.omlx/.restart-required"

# Keep restart intent across failed runs, even if the old server stays healthy.
require_restart() {
    mkdir -p "$HOME/.omlx"
    touch "$restart_required"
}

prefix="$(brew --prefix omlx)"
python="$prefix/libexec/bin/python"

if ! "$python" -c 'import xgrammar' >/dev/null 2>&1; then
    require_restart
    brew reinstall "$formula" --with-grammar
    prefix="$(brew --prefix omlx)"
    python="$prefix/libexec/bin/python"
fi

if ! "$python" -c 'import xgrammar' >/dev/null 2>&1; then
    site="$prefix/libexec/lib/python3.11/site-packages"
    dylib="$site/xgrammar/libxgrammar_bindings.dylib"
    tvm_lib="$site/tvm_ffi/lib"
    dist_info=("$site"/xgrammar-*.dist-info)
    record="${dist_info[0]}/RECORD"

    [[ -f "$dylib" && -d "$tvm_lib" && -d "${dist_info[0]}" ]]
    if ! /usr/bin/otool -l "$dylib" | grep -Fq "$tvm_lib"; then
        /usr/bin/install_name_tool -add_rpath "$tvm_lib" "$dylib"
    fi
    /usr/bin/codesign --force --sign - "$dylib"
    if ! grep -Fqx 'xgrammar/libxgrammar_bindings.dylib,,' "$record"; then
        printf 'xgrammar/libxgrammar_bindings.dylib,,\n' >> "$record"
    fi
    "$python" -c 'import xgrammar'
fi

mkdir -p "$(dirname "$settings_file")"
base_settings="$(mktemp)"
expanded_overlay="$(mktemp)"
merged_settings="$(mktemp)"
cleanup() { rm -f "$base_settings" "$expanded_overlay" "$merged_settings"; }
trap cleanup EXIT

if [[ -f "$settings_file" ]]; then
    cp "$settings_file" "$base_settings"
else
    printf '{}\n' > "$base_settings"
fi
jq --arg home "$HOME" \
    'walk(if type == "string" then gsub("\\$\\{HOME\\}"; $home) else . end)' \
    "$settings_overlay" > "$expanded_overlay"
jq -s '.[0] * .[1]' "$base_settings" "$expanded_overlay" > "$merged_settings"
if [[ ! -f "$settings_file" ]] || ! cmp -s "$settings_file" "$merged_settings"; then
    require_restart
    install -m 600 "$merged_settings" "$settings_file"
fi

model_files_complete() {
    local shard
    # This pinned model has five shards; update the check when replacing it.
    [[ -s "$model_dir/model.safetensors.index.json" ]] || return 1
    for shard in 00001 00002 00003 00004 00005; do
        [[ -s "$model_dir/model-${shard}-of-00005.safetensors" ]] || return 1
    done
}

model_complete() {
    model_files_complete &&
        [[ -f "$model_revision_file" ]] &&
        [[ "$(< "$model_revision_file")" == "$model_revision" ]]
}

if ! model_complete; then
    require_restart
    "$prefix/libexec/bin/hf" download "$model_repo" \
        --revision "$model_revision" --local-dir "$model_dir"
    if ! model_files_complete; then
        printf 'oMLX model download is incomplete: %s\n' "$model_dir" >&2
        exit 1
    fi
    printf '%s\n' "$model_revision" > "$model_revision_file"
fi

health_url="http://127.0.0.1:8000/health"
server_healthy() {
    # oMLX exposes this endpoint without authentication and returns 503 while loading.
    curl --fail --silent --connect-timeout 2 --max-time 5 "$@" "$health_url" |
        jq -es 'length == 1 and .[0].status == "healthy" and
            (.[0].engine_pool.model_count | type == "number" and . > 0)' >/dev/null
}

if [[ -f "$restart_required" ]] || ! server_healthy; then
    require_restart
    brew services restart "$formula"
fi

if ! server_healthy --show-error --retry 30 --retry-connrefused --retry-delay 2 --retry-max-time 120; then
    printf 'oMLX did not become healthy at %s\n' "$health_url" >&2
    exit 1
fi
rm -f "$restart_required"

printf 'oMLX ready: xgrammar + %s@%s\n' "$model_repo" "$model_revision"
