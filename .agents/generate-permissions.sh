#!/bin/bash
# Generate tiered permission profiles from safe-commands.yaml
#
# Usage:
#   ./generate-permissions.sh              # Generate all profiles
#   ./generate-permissions.sh claude       # Claude Code profiles only
#   ./generate-permissions.sh continue     # Continue.dev (uses dev tier)
#
# Profiles (cumulative — each includes all tiers below it):
#   scout — read-only research & exploration
#   dev   — safe, productive daily development (default)
#   yolo  — full access, just do it
#
# Outputs:
#   ~/.claude/profiles/{scout,dev,yolo}.json   (Claude Code)
#   ~/.claude/settings.json                     (dev profile as default)
#   ~/.continue/permissions.yaml                (Continue.dev, dev tier)

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
YAML_FILE="$SCRIPT_DIR/safe-commands.yaml"
PROFILES_DIR="$HOME/.claude/profiles"

# Source print utils if available
if [[ -n "${print_section:-}" ]] || source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null; then
    :
fi

check_deps() {
    local missing=()
    command -v yq >/dev/null 2>&1 || missing+=("yq")
    command -v jq >/dev/null 2>&1 || missing+=("jq")

    if [[ ${#missing[@]} -gt 0 ]]; then
        print_warning "Missing required tools: ${missing[*]} (brew install ${missing[*]})"
        return 1
    fi
}

# Get category names for a tier (cumulative: yolo includes dev includes scout)
get_tier_categories() {
    local tier="$1"
    local categories=""

    # Scout categories are always included
    categories=$(yq eval '._tiers.scout[]' "$YAML_FILE" 2>/dev/null)

    if [[ "$tier" == "dev" || "$tier" == "yolo" ]]; then
        categories="$categories"$'\n'$(yq eval '._tiers.dev[]' "$YAML_FILE" 2>/dev/null)
    fi

    if [[ "$tier" == "yolo" ]]; then
        categories="$categories"$'\n'$(yq eval '._tiers.yolo[]' "$YAML_FILE" 2>/dev/null)
    fi

    echo "$categories" | grep -v '^$' | sort -u
}

# Get bash commands for a specific category
get_category_commands() {
    local category="$1"
    yq eval ".${category}[]" "$YAML_FILE" 2>/dev/null | grep -v '^$'
}

# Get all bash commands for a tier
get_tier_commands() {
    local tier="$1"
    while IFS= read -r category; do
        [[ -z "$category" ]] && continue
        get_category_commands "$category"
    done < <(get_tier_categories "$tier") | sort -u
}

# Get non-bash tool permissions for a tier (cumulative)
get_tier_tools() {
    local tier="$1"
    local tools=""

    tools=$(yq eval '._tools.scout[]' "$YAML_FILE" 2>/dev/null)

    if [[ "$tier" == "dev" || "$tier" == "yolo" ]]; then
        tools="$tools"$'\n'$(yq eval '._tools.dev[]' "$YAML_FILE" 2>/dev/null)
    fi

    if [[ "$tier" == "yolo" ]]; then
        tools="$tools"$'\n'$(yq eval '._tools.yolo[]' "$YAML_FILE" 2>/dev/null)
    fi

    echo "$tools" | grep -v '^$' | grep -v '^null$' | sort -u
}

# Get deny rules for a specific tier
get_tier_deny() {
    local tier="$1"
    yq eval "._deny.${tier}[]" "$YAML_FILE" 2>/dev/null | grep -v '^$'
}

# Build a JSON allow array for a tier
build_allow_json() {
    local tier="$1"
    local entries=()

    # Bash commands
    while IFS= read -r cmd; do
        [[ -z "$cmd" || "$cmd" =~ ^# ]] && continue
        cmd="${cmd//\"/\\\"}"
        local pattern="${cmd% \*}"
        entries+=("\"Bash(${pattern}:*)\"")
    done < <(get_tier_commands "$tier")

    # Non-bash tools
    while IFS= read -r tool; do
        [[ -z "$tool" ]] && continue
        entries+=("\"${tool}\"")
    done < <(get_tier_tools "$tier")

    # Output JSON array
    echo -n '['
    local first=true
    for entry in "${entries[@]}"; do
        [[ "$first" == "true" ]] && first=false || echo -n ','
        echo -n "$entry"
    done
    echo -n ']'
}

# Build a JSON deny array for a tier
build_deny_json() {
    local tier="$1"
    local entries=()

    while IFS= read -r cmd; do
        [[ -z "$cmd" || "$cmd" =~ ^# ]] && continue
        cmd="${cmd//\"/\\\"}"
        local pattern="${cmd% \*}"
        entries+=("\"Bash(${pattern}:*)\"")
    done < <(get_tier_deny "$tier")

    echo -n '['
    local first=true
    for entry in "${entries[@]}"; do
        [[ "$first" == "true" ]] && first=false || echo -n ','
        echo -n "$entry"
    done
    echo -n ']'
}

# Generate a single profile JSON file (permissions only)
generate_profile() {
    local tier="$1"
    local output="$PROFILES_DIR/${tier}.json"

    local allow_json deny_json
    allow_json=$(build_allow_json "$tier")
    deny_json=$(build_deny_json "$tier")

    echo "{\"permissions\":{\"allow\":$allow_json,\"deny\":$deny_json}}" | jq '.' > "$output"

    local allow_count deny_count
    allow_count=$(jq '.permissions.allow | length' "$output")
    deny_count=$(jq '.permissions.deny | length' "$output")
    print_success "$tier: $allow_count allow, $deny_count deny"
}

# Merge dev profile as default into settings.json
apply_default_profile() {
    local settings_file="$HOME/.claude/settings.json"
    local dev_profile="$PROFILES_DIR/dev.json"

    [[ -f "$settings_file" ]] || echo '{}' > "$settings_file"
    cp "$settings_file" "$settings_file.bak"

    local allow_json deny_json
    allow_json=$(jq '.permissions.allow' "$dev_profile")
    deny_json=$(jq '.permissions.deny' "$dev_profile")

    jq --argjson allow "$allow_json" --argjson deny "$deny_json" \
        '.permissions.allow = $allow | .permissions.deny = $deny' \
        "$settings_file.bak" > "$settings_file"
}

# Generate Claude Code profiles
generate_claude() {
    mkdir -p "$PROFILES_DIR"

    print_step "Generating permission profiles"
    generate_profile "scout"
    generate_profile "dev"
    generate_profile "yolo"

    apply_default_profile
    print_info "Default profile: dev (use cc --scout or cc --yolo to override)"
}

# Generate Continue.dev permissions (dev tier)
generate_continue() {
    local output="$HOME/.continue/permissions.yaml"

    mkdir -p "$HOME/.continue"
    print_step "Generating Continue.dev permissions (dev tier)"

    cat > "$output" <<'HEADER'
# Auto-generated from dotfiles/.agents/safe-commands.yaml (dev tier)
# Regenerate with: ~/dotfiles/.agents/generate-permissions.sh continue

allow:
HEADER

    while IFS= read -r cmd; do
        [[ -z "$cmd" || "$cmd" =~ ^# ]] && continue
        local pattern="${cmd% \*}"
        echo "  - Bash($pattern*)" >> "$output"
    done < <(get_tier_commands "dev")

    print_success "Continue.dev: $(grep -c 'Bash(' "$output") permission rules"
}

# Main
check_deps || exit 0

case "${1:-all}" in
    claude)   generate_claude ;;
    continue) generate_continue ;;
    all)      generate_claude; generate_continue ;;
    *)        echo "Usage: $0 [claude|continue|all]"; exit 1 ;;
esac
