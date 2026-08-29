#!/usr/bin/env bash
set -euo pipefail

formula="jundot/omlx/omlx"
model_repo="Jundot/Qwen3.6-35B-A3B-oQ4e-mtp"
model_dir="$HOME/.omlx/models/$model_repo"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
settings_overlay="$script_dir/omlx/settings.json"
settings_file="$HOME/.omlx/settings.json"
changed=false

prefix="$(brew --prefix omlx)"
python="$prefix/libexec/bin/python"

if ! "$python" -c 'import xgrammar' >/dev/null 2>&1; then
    brew reinstall "$formula" --with-grammar
    prefix="$(brew --prefix omlx)"
    python="$prefix/libexec/bin/python"
    changed=true
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
    printf 'xgrammar/libxgrammar_bindings.dylib,,\n' > "$record"
    "$python" -c 'import xgrammar'
    changed=true
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
    install -m 600 "$merged_settings" "$settings_file"
    changed=true
fi

model_complete=true
[[ -f "$model_dir/model.safetensors.index.json" ]] || model_complete=false
for shard in 00001 00002 00003 00004 00005; do
    [[ -f "$model_dir/model-${shard}-of-00005.safetensors" ]] || model_complete=false
done

if [[ "$model_complete" != true ]]; then
    "$prefix/libexec/bin/hf" download "$model_repo" --local-dir "$model_dir"
    changed=true
fi

if [[ "$changed" == true ]]; then
    brew services restart "$formula"
fi

printf 'oMLX ready: xgrammar + %s\n' "$model_repo"
