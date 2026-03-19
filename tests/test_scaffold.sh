#!/usr/bin/env bash
# =============================================================================
# Scaffold Eval Framework
# =============================================================================
# Validates that our prompt scaffolding produces correct, consistent output.
#
# Three tiers:
#   1. Static validation  — Files parse, required files exist, tools referenced are real
#   2. Consistency checks  — Rules agree with each other across files
#   3. Completeness checks — Every recipe produces all required artifacts
#
# Usage:
#   ./tests/test_scaffold.sh          # Run all tests
#   ./tests/test_scaffold.sh --quick  # Static validation only
# =============================================================================

# No set -e: this is a test runner that handles failures explicitly
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCAFFOLD="$DOTFILES_DIR/prompts/scaffold.sh"
RULES_DIR="$DOTFILES_DIR/.ai/rules"
PROMPTS_DIR="$DOTFILES_DIR/prompts"
TMPDIR_BASE="${TMPDIR:-/tmp}/scaffold-eval-$$"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
QUICK=false

[[ "${1:-}" == "--quick" ]] && QUICK=true

cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

mkdir -p "$TMPDIR_BASE"

# --- Test helpers ---

pass() {
    ((PASS++))
    echo -e "  ${GREEN}✓${NC} $1"
}

fail() {
    ((FAIL++))
    echo -e "  ${RED}✗${NC} $1"
}

warn() {
    ((WARN++))
    echo -e "  ${YELLOW}!${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

# =============================================================================
# TIER 1: Static Validation
# =============================================================================

section "Tier 1: Static Validation"

# --- All .mdc files have valid frontmatter ---
echo ""
echo "  Rule file frontmatter:"
for rule in "$RULES_DIR"/**/*.mdc "$RULES_DIR"/*.mdc; do
    [[ -f "$rule" ]] || continue
    name="$(basename "$rule")"

    # Check frontmatter exists
    if ! head -1 "$rule" | grep -q '^---$'; then
        fail "$name: missing frontmatter (no opening ---)"
        continue
    fi

    # Check frontmatter closes
    if ! awk 'NR>1' "$rule" | grep -q '^---$'; then
        fail "$name: missing frontmatter closing ---"
        continue
    fi

    # Check required field: description (extract between first and second ---)
    if ! sed -n '2,/^---$/p' "$rule" | grep -q '^description:'; then
        fail "$name: missing 'description' in frontmatter"
        continue
    fi

    pass "$name"
done

# --- Template files parse ---
echo ""
echo "  Template file validity:"

# Check TOML files parse (if python available)
if command -v python3 >/dev/null 2>&1; then
    for toml in "$PROMPTS_DIR"/*/templates/pyproject.toml "$PROMPTS_DIR"/*/*/templates/pyproject.toml; do
        [[ -f "$toml" ]] || continue
        rel="${toml#"$DOTFILES_DIR/"}"
        if python3 -c "
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
with open('$toml', 'rb') as f:
    tomllib.load(f)
" 2>/dev/null; then
            pass "$rel: valid TOML"
        else
            fail "$rel: invalid TOML"
        fi
    done
fi

# Check YAML files parse (if yq available)
if command -v yq >/dev/null 2>&1; then
    for yaml in "$PROMPTS_DIR"/*/templates/lefthook.yml "$PROMPTS_DIR"/*/*/templates/lefthook.yml; do
        [[ -f "$yaml" ]] || continue
        rel="${yaml#"$DOTFILES_DIR/"}"
        if yq '.' "$yaml" >/dev/null 2>&1; then
            pass "$rel: valid YAML"
        else
            fail "$rel: invalid YAML"
        fi
    done
fi

# Check JSON files parse (if jq available)
if command -v jq >/dev/null 2>&1; then
    for json in "$PROMPTS_DIR"/*/templates/biome.json "$PROMPTS_DIR"/*/*/templates/biome.json \
                "$DOTFILES_DIR"/agents/claude/hooks.json \
                "$DOTFILES_DIR"/agents/claude/marketplaces.json; do
        [[ -f "$json" ]] || continue
        rel="${json#"$DOTFILES_DIR/"}"
        if jq '.' "$json" >/dev/null 2>&1; then
            pass "$rel: valid JSON"
        else
            fail "$rel: invalid JSON"
        fi
    done
fi

# --- Tools referenced in rules actually exist ---
echo ""
echo "  Tool references in rules:"

check_tool_ref() {
    local tool="$1"
    local rule_file="$2"
    local rule_name
    rule_name="$(basename "$rule_file")"
    if command -v "$tool" >/dev/null 2>&1; then
        pass "$rule_name references '$tool' (found)"
    else
        warn "$rule_name references '$tool' (not installed)"
    fi
}

# Extract tool references from stack rules
for stack_rule in "$RULES_DIR"/tooling/stack-*.mdc; do
    [[ -f "$stack_rule" ]] || continue
    case "$(basename "$stack_rule")" in
        stack-python.mdc)
            check_tool_ref "uv" "$stack_rule"
            check_tool_ref "ruff" "$stack_rule" 2>/dev/null || warn "ruff not in PATH (installed via uv)"
            ;;
        stack-typescript.mdc)
            check_tool_ref "bun" "$stack_rule"
            ;;
        stack-golang.mdc)
            check_tool_ref "go" "$stack_rule"
            check_tool_ref "golangci-lint" "$stack_rule"
            ;;
        stack-rust.mdc)
            check_tool_ref "cargo" "$stack_rule"
            ;;
    esac
done

check_tool_ref "just" "$RULES_DIR/tooling/stack-python.mdc"
check_tool_ref "lefthook" "$RULES_DIR/tooling/stack-python.mdc"
check_tool_ref "gh" "$RULES_DIR/process/github-workflow.mdc"
check_tool_ref "shellcheck" "$DOTFILES_DIR/agents/claude/agents/shellcheck-reviewer.md"

# =============================================================================
# TIER 2: Consistency Checks
# =============================================================================

section "Tier 2: Consistency Checks"

echo ""
echo "  Cross-file tool agreement:"

# Python type checker consistency
py_type_checker_refs=()
for f in "$RULES_DIR/languages/python.mdc" "$RULES_DIR/tooling/stack-python.mdc"; do
    [[ -f "$f" ]] || continue
    if grep -qi 'pyright' "$f" && ! grep -qi 'not.*pyright\|avoid.*pyright\|Pyright.*Node' "$f"; then
        py_type_checker_refs+=("$(basename "$f"):pyright")
    fi
    if grep -qi '\bty\b' "$f" && ! grep -qi 'not.*\bty\b\|avoid.*\bty\b' "$f"; then
        py_type_checker_refs+=("$(basename "$f"):ty")
    fi
done

# Check templates match rules
for toml in "$PROMPTS_DIR"/python/templates/pyproject.toml "$PROMPTS_DIR"/python/cli/templates/pyproject.toml; do
    [[ -f "$toml" ]] || continue
    rel="${toml#"$DOTFILES_DIR/"}"
    if grep -q '"pyright' "$toml"; then
        py_type_checker_refs+=("$rel:pyright")
    fi
    if grep -q '"ty' "$toml" || grep -q 'tool\.ty' "$toml"; then
        py_type_checker_refs+=("$rel:ty")
    fi
done

# Check lefthook templates match
for yml in "$PROMPTS_DIR"/python/templates/lefthook.yml "$PROMPTS_DIR"/python/cli/templates/lefthook.yml; do
    [[ -f "$yml" ]] || continue
    rel="${yml#"$DOTFILES_DIR/"}"
    if grep -q 'pyright' "$yml"; then
        py_type_checker_refs+=("$rel:pyright")
    fi
    if grep -q 'ty check\|ty:' "$yml"; then
        py_type_checker_refs+=("$rel:ty")
    fi
done

# Check justfile templates match
for justfile in "$PROMPTS_DIR"/python/templates/justfile "$PROMPTS_DIR"/python/cli/templates/justfile; do
    [[ -f "$justfile" ]] || continue
    rel="${justfile#"$DOTFILES_DIR/"}"
    if grep -q 'pyright' "$justfile"; then
        py_type_checker_refs+=("$rel:pyright")
    fi
    if grep -q 'ty check\|ty$' "$justfile"; then
        py_type_checker_refs+=("$rel:ty")
    fi
done

# Analyze: all refs should agree on the same tool
tools_used=$(printf '%s\n' "${py_type_checker_refs[@]}" | sed 's/.*://' | sort -u)
tool_count=$(echo "$tools_used" | wc -l | tr -d ' ')

if [[ "$tool_count" -eq 1 ]]; then
    pass "Python type checker consistent: all files use '$tools_used'"
elif [[ "$tool_count" -gt 1 ]]; then
    fail "Python type checker INCONSISTENT across files:"
    for ref in "${py_type_checker_refs[@]}"; do
        echo -e "       ${ref%%:*} → ${ref##*:}"
    done
fi

# Python version consistency
py_versions=()
for f in "$RULES_DIR/tooling/stack-python.mdc" \
         "$PROMPTS_DIR/python/templates/pyproject.toml" \
         "$PROMPTS_DIR/python/cli/templates/pyproject.toml"; do
    [[ -f "$f" ]] || continue
    rel="${f#"$DOTFILES_DIR/"}"
    ver=$(grep -oE '3\.[0-9]+' "$f" | head -1)
    [[ -n "$ver" ]] && py_versions+=("$rel:$ver")
done
versions_used=$(printf '%s\n' "${py_versions[@]}" | sed 's/.*://' | sort -u)
version_count=$(echo "$versions_used" | wc -l | tr -d ' ')

if [[ "$version_count" -eq 1 ]]; then
    pass "Python version consistent: $versions_used"
elif [[ "$version_count" -gt 1 ]]; then
    warn "Python version varies across files (may be intentional):"
    for ref in "${py_versions[@]}"; do
        echo -e "       ${ref%%:*} → ${ref##*:}"
    done
fi

# Claude plugin consistency — LSP should match type checker
echo ""
echo "  Plugin-rule alignment:"
plugins_file="$DOTFILES_DIR/agents/claude/plugins.yaml"
if [[ -f "$plugins_file" ]]; then
    if grep -q 'ty-lsp' "$plugins_file" && echo "$tools_used" | grep -q 'ty'; then
        pass "LSP plugin (ty-lsp) matches type checker choice (ty)"
    elif grep -q 'pyright-lsp' "$plugins_file" && echo "$tools_used" | grep -q 'pyright'; then
        pass "LSP plugin (pyright-lsp) matches type checker choice (pyright)"
    elif grep -q 'pyright-lsp' "$plugins_file" && echo "$tools_used" | grep -q 'ty'; then
        fail "LSP plugin is pyright-lsp but rules specify ty"
    elif grep -q 'ty-lsp' "$plugins_file" && echo "$tools_used" | grep -q 'pyright'; then
        fail "LSP plugin is ty-lsp but rules specify pyright"
    fi
fi

# Scaffold script lists all universal rules that exist
echo ""
echo "  Scaffold completeness:"
scaffold_rules=$(grep -oP "'[^']+\.mdc'" "$SCAFFOLD" 2>/dev/null | tr -d "'" | sort -u || true)
if [[ -z "$scaffold_rules" ]]; then
    # Try without -P (macOS grep)
    scaffold_rules=$(grep -o '"[^"]*\.mdc"' "$SCAFFOLD" 2>/dev/null | tr -d '"' | sort -u || true)
fi

# Check universal rules in scaffold match what exists in process/
for rule_file in "$RULES_DIR"/process/*.mdc; do
    [[ -f "$rule_file" ]] || continue
    rule_name="$(basename "$rule_file")"
    rel_path="process/$rule_name"
    if grep -q "$rel_path" "$SCAFFOLD" 2>/dev/null || grep -q "$rule_name" "$SCAFFOLD" 2>/dev/null; then
        pass "Scaffold includes $rule_name"
    else
        warn "Scaffold does NOT include $rule_name (may be intentional)"
    fi
done

# =============================================================================
# TIER 3: Scaffold Output Validation
# =============================================================================

if [[ "$QUICK" == true ]]; then
    section "Tier 3: Skipped (--quick mode)"
else
    section "Tier 3: Scaffold Output Validation"

    RECIPES=("typescript:svelte" "python:fastapi" "python:cli" "golang:chi" "rust:axum")

    for combo in "${RECIPES[@]}"; do
        recipe="${combo%%:*}"
        app_type="${combo##*:}"
        project_dir="$TMPDIR_BASE/test-$recipe-$app_type"

        echo ""
        echo -e "  ${BLUE}Testing $recipe/$app_type scaffold:${NC}"

        # Run scaffold
        if "$SCAFFOLD" "$recipe" "$app_type" "$project_dir" >/dev/null 2>&1; then
            pass "scaffold.sh exited 0"
        else
            fail "scaffold.sh failed"
            continue
        fi

        # Required files
        for required in AGENTS.md .ai/rules .ai/artifacts/decisions/_index.md; do
            if [[ -e "$project_dir/$required" ]]; then
                pass "$required exists"
            else
                fail "$required missing"
            fi
        done

        # Check .cursor/rules symlinks exist and point to .ai/rules
        if [[ -d "$project_dir/.cursor/rules" ]]; then
            broken_links=0
            for link in "$project_dir/.cursor/rules/"*.mdc; do
                [[ -L "$link" ]] || continue
                if [[ ! -e "$link" ]]; then
                    ((broken_links++))
                fi
            done
            if [[ "$broken_links" -eq 0 ]]; then
                pass ".cursor/rules/ symlinks valid"
            else
                fail ".cursor/rules/ has $broken_links broken symlinks"
            fi
        else
            fail ".cursor/rules/ directory missing"
        fi

        # Check template files exist based on recipe
        case "$recipe" in
            typescript)
                [[ -f "$project_dir/biome.json" ]] && pass "biome.json" || warn "biome.json missing"
                ;;
            python)
                [[ -f "$project_dir/pyproject.toml" ]] && pass "pyproject.toml" || fail "pyproject.toml missing"
                ;;
        esac

        # Common template files
        [[ -f "$project_dir/justfile" ]] && pass "justfile" || warn "justfile missing"
        [[ -f "$project_dir/lefthook.yml" ]] && pass "lefthook.yml" || warn "lefthook.yml missing"

        # Check git was initialized
        [[ -d "$project_dir/.git" ]] && pass "git initialized" || warn "git not initialized"

        # AGENTS.md should reference .ai/rules
        if grep -q '\.ai/rules' "$project_dir/AGENTS.md" 2>/dev/null; then
            pass "AGENTS.md references .ai/rules"
        else
            fail "AGENTS.md doesn't reference .ai/rules"
        fi

        # Check no stale tool references in generated files
        if [[ "$recipe" == "python" ]]; then
            if grep -q '"pyright' "$project_dir/pyproject.toml" 2>/dev/null; then
                fail "pyproject.toml still references pyright (should be ty)"
            else
                pass "pyproject.toml uses correct type checker"
            fi
        fi
    done

    # Test idempotency — re-running should not break anything
    echo ""
    echo -e "  ${BLUE}Idempotency test:${NC}"
    idempotent_dir="$TMPDIR_BASE/test-idempotent"

    "$SCAFFOLD" python fastapi "$idempotent_dir" >/dev/null 2>&1
    first_agents_md=$(cat "$idempotent_dir/AGENTS.md")

    "$SCAFFOLD" python fastapi "$idempotent_dir" >/dev/null 2>&1
    second_agents_md=$(cat "$idempotent_dir/AGENTS.md")

    if [[ "$first_agents_md" == "$second_agents_md" ]]; then
        pass "AGENTS.md unchanged on re-run (idempotent)"
    else
        fail "AGENTS.md changed on re-run (not idempotent)"
    fi

    # Test --tools all creates symlinks to AGENTS.md (not shim files)
    echo ""
    echo -e "  ${BLUE}Root symlink test (--tools all):${NC}"
    symlink_dir="$TMPDIR_BASE/test-symlinks"

    "$SCAFFOLD" python fastapi "$symlink_dir" --tools all >/dev/null 2>&1

    for root_file in GEMINI.md CODEX.md; do
        if [[ -L "$symlink_dir/$root_file" ]]; then
            target=$(readlink "$symlink_dir/$root_file")
            if [[ "$target" == "AGENTS.md" ]]; then
                pass "$root_file is symlink → AGENTS.md"
            else
                fail "$root_file symlinks to $target (expected AGENTS.md)"
            fi
        elif [[ -f "$symlink_dir/$root_file" ]]; then
            fail "$root_file is a regular file (expected symlink)"
        else
            fail "$root_file missing"
        fi
    done

    # Symlinks should resolve to readable content
    if [[ -r "$symlink_dir/GEMINI.md" ]] && grep -q '\.ai/rules' "$symlink_dir/GEMINI.md" 2>/dev/null; then
        pass "GEMINI.md symlink resolves to AGENTS.md content"
    else
        fail "GEMINI.md symlink doesn't resolve correctly"
    fi
fi

# =============================================================================
# Summary
# =============================================================================

section "Results"
echo ""
echo -e "  ${GREEN}Passed: $PASS${NC}"
[[ $WARN -gt 0 ]] && echo -e "  ${YELLOW}Warnings: $WARN${NC}"
[[ $FAIL -gt 0 ]] && echo -e "  ${RED}Failed: $FAIL${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}EVAL FAILED${NC} — $FAIL issues need attention"
    exit 1
else
    echo -e "${GREEN}EVAL PASSED${NC}"
    exit 0
fi
