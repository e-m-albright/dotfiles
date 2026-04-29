#!/usr/bin/env bash
# =============================================================================
# Project Scaffold Script
# =============================================================================
# Creates or updates a project with cross-vendor AI rules.
# Safe to run multiple times — idempotent.
#
# Philosophy: Dotfiles seeds and influences. Projects own themselves.
# - All .ai/rules/ are COPIED (project owns them, re-run --force to update)
# - Tool rule dirs get relative symlinks to .ai/rules/ for discovery
# - AGENTS.md is GENERATED once, then project-owned (never overwritten)
#
# Usage:
#   ./prompts/scaffold.sh <recipe> [app-type] <project-path> [--tools list]
#   ./prompts/scaffold.sh --force <recipe> [app-type] <project-path>
#
# Examples:
#   ./prompts/scaffold.sh typescript svelte my-new-app
#   ./prompts/scaffold.sh typescript svelte .
#   ./prompts/scaffold.sh typescript my-app               # Defaults to svelte
#   ./prompts/scaffold.sh python .                        # Defaults to fastapi
#   ./prompts/scaffold.sh golang chi ~/projects/my-svc
#   ./prompts/scaffold.sh --force python .                # Force regenerate all
#   ./prompts/scaffold.sh python my-api --tools copilot,gemini
#   ./prompts/scaffold.sh --tools all python my-api
# =============================================================================

set -eo pipefail

# Get script directory (where dotfiles/prompts lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AI_RULES_DIR="$DOTFILES_DIR/.ai/rules"

FORCE=false
SCAFFOLD_TOOLS="cursor"
WITH_AUDIT_PIPELINE=false
WITH_BASELINES=false

# Source shared print functions
source "$DOTFILES_DIR/macos/print_utils.sh"

# Add manifest header to a copied rule file for staleness tracking
# Usage: add_manifest_header <dest_file> <source_rule_path>
add_manifest_header() {
    local dest="$1"
    local rule_path="$2"
    local datestamp
    datestamp="$(date +%Y-%m-%d)"
    local header="<!-- source: dotfiles/.ai/rules/$rule_path | $datestamp -->"

    # If file already has a manifest header, replace it
    if head -1 "$dest" | grep -q '^<!-- source:'; then
        local tmp
        tmp="$(mktemp)"
        echo "$header" > "$tmp"
        tail -n +2 "$dest" >> "$tmp"
        mv "$tmp" "$dest"
    else
        local tmp
        tmp="$(mktemp)"
        echo "$header" > "$tmp"
        cat "$dest" >> "$tmp"
        mv "$tmp" "$dest"
    fi
}

# =============================================================================
# Recipe → rule mappings (copied — project can customize)
# =============================================================================
get_recipe_rules() {
    local recipe="$1"
    local app_type="$2"

    # Language + stack rules per recipe
    case "$recipe" in
        typescript)
            echo "languages/typescript.mdc"
            echo "tooling/stack-typescript.mdc"
            echo "tooling/services.mdc"
            ;;
        python)
            echo "languages/python.mdc"
            echo "tooling/stack-python.mdc"
            echo "tooling/services.mdc"
            echo "process/shell-automation.mdc"
            ;;
        golang)
            echo "languages/golang.mdc"
            echo "tooling/stack-golang.mdc"
            echo "tooling/services.mdc"
            echo "process/shell-automation.mdc"
            ;;
        rust)
            echo "languages/rust.mdc"
            echo "tooling/stack-rust.mdc"
            echo "tooling/services.mdc"
            echo "process/shell-automation.mdc"
            ;;
    esac

    # Framework rules per app-type
    case "$recipe/$app_type" in
        typescript/svelte)  echo "frameworks/sveltekit.mdc" ;;
        typescript/astro)   echo "frameworks/astro.mdc" ;;
        python/fastapi)     echo "frameworks/fastapi.mdc" ;;
        python/cli)         ;; # CLI uses language + stack rules only, no framework rule
        golang/chi)         echo "frameworks/chi.mdc" ;;
        rust/axum)          echo "frameworks/axum.mdc" ;;
        rust/tauri)         echo "frameworks/tauri.mdc" ;;
    esac
}

# Print functions are provided by print_utils.sh (sourced above)

get_default_app_type() {
    local recipe="$1"
    case "$recipe" in
        typescript) echo "svelte" ;;
        python) echo "fastapi" ;;
        golang) echo "chi" ;;
        rust) echo "axum" ;;
        *) echo "" ;;
    esac
}

is_valid_app_type() {
    local recipe="$1"
    local app_type="$2"
    local template_dir="$PROMPTS_DIR/$recipe/$app_type/templates"
    # Valid if there's a templates dir for this app-type, or it's a known combo
    [[ -d "$template_dir" ]] || [[ -d "$PROMPTS_DIR/$recipe/templates" ]]
}

is_known_app_type() {
    local combo="$1/$2"
    case "$combo" in
        typescript/svelte|typescript/astro|python/fastapi|python/cli|golang/chi|rust/axum|rust/tauri)
            return 0 ;;
        *)
            return 1 ;;
    esac
}

is_existing_path() {
    local path="$1"
    [[ "$path" == "." ]] || [[ -d "$path" ]]
}

# Copy a rule file into .ai/rules/ (recipe-specific — project can customize)
copy_ai_rule() {
    local rule_path="$1"  # e.g., "languages/python.mdc"
    local rule_name
    rule_name="$(basename "$rule_path")"
    local source="$AI_RULES_DIR/$rule_path"

    if [[ ! -f "$source" ]]; then
        print_warning "Rule not found in dotfiles: $rule_path"
        return
    fi

    if [[ -f ".ai/rules/$rule_name" ]] && [[ "$FORCE" != true ]]; then
        print_skip ".ai/rules/$rule_name"
        return
    fi

    cp "$source" ".ai/rules/$rule_name"
    add_manifest_header ".ai/rules/$rule_name" "$rule_path"
    if [[ "$FORCE" == true ]]; then
        print_update ".ai/rules/$rule_name (force copied)"
    else
        print_step "Copied .ai/rules/$rule_name"
    fi
}

# Create symlinks from tool-specific rule dirs → .ai/rules/ for tool discovery.
# Reads agents/shared/tool-targets.json for directory conventions.
# Falls back to Cursor-only if jq is not available.
setup_tool_symlinks() {
    local registry="$DOTFILES_DIR/agents/shared/tool-targets.json"
    local tools_filter="$SCAFFOLD_TOOLS"

    if [[ ! -f "$registry" ]] || ! command -v jq >/dev/null 2>&1; then
        if [[ "$tools_filter" == *"cursor"* || "$tools_filter" == "all" ]]; then
            _symlink_rules_for_tool ".cursor/rules" ".mdc" "../../"
        fi
        return
    fi

    # Read each tool with strategy=symlink from registry, filtered by SCAFFOLD_TOOLS
    local tools
    if [[ "$tools_filter" == "all" ]]; then
        tools=$(jq -r '.tools | to_entries[] | select(.value.strategy == "symlink") | .key' "$registry")
    else
        tools=$(jq -r --arg filter "$tools_filter" '
            .tools | to_entries[]
            | select(.value.strategy == "symlink")
            | select(.key as $k | $filter | split(",") | index($k))
            | .key
        ' "$registry")
    fi

    for tool in $tools; do
        local rules_dir suffix prefix
        rules_dir=$(jq -r ".tools[\"$tool\"].rulesDir" "$registry")
        suffix=$(jq -r ".tools[\"$tool\"].suffix" "$registry")
        prefix=$(jq -r ".tools[\"$tool\"].symlinkPrefix" "$registry")

        _symlink_rules_for_tool "$rules_dir" "$suffix" "$prefix"
    done
}

# Create symlinks in a tool's rule dir pointing to .ai/rules/ files
# Usage: _symlink_rules_for_tool <rules_dir> <suffix> <symlink_prefix>
_symlink_rules_for_tool() {
    local rules_dir="$1"
    local suffix="$2"
    local prefix="$3"
    local tool_name
    tool_name="$(echo "$rules_dir" | cut -d/ -f1 | sed 's/^\.//')"

    mkdir -p "$rules_dir"

    for rule_file in .ai/rules/*.mdc; do
        [[ -f "$rule_file" ]] || continue
        local rule_name base_name target_name tool_link
        rule_name="$(basename "$rule_file")"
        base_name="${rule_name%.mdc}"

        # Target filename uses the tool's expected suffix
        if [[ "$suffix" == ".mdc" ]]; then
            target_name="$rule_name"
        else
            target_name="${base_name}${suffix}"
        fi

        tool_link="$rules_dir/$target_name"

        if [[ -L "$tool_link" ]]; then
            local current_target
            current_target="$(readlink "$tool_link")"
            if [[ "$current_target" == "${prefix}.ai/rules/$rule_name" ]]; then
                continue
            fi
            rm "$tool_link"
        elif [[ -f "$tool_link" ]]; then
            if [[ "$FORCE" != true ]]; then
                continue
            fi
            rm "$tool_link"
        fi

        ln -s "${prefix}.ai/rules/$rule_name" "$tool_link"
    done
    print_step "Symlinks: $rules_dir/ → .ai/rules/ ($tool_name)"
}

show_help() {
    cat << EOF
Project Scaffold Script

Creates or updates a project with cross-vendor AI rules.
Safe to run multiple times — only adds missing pieces.

Usage:
  $(basename "$0") [--force] [--tools <list>] <recipe> [app-type] <project-path>

Arguments:
  --force        Force regenerate AGENTS.md and overwrite existing rules
  --tools <list> Comma-separated list of tools to set up symlinks for.
                 Default: cursor (claude reads .ai/rules/ directly via CLAUDE.md)
                 Use "all" for every tool in the registry.
                 Available: cursor, copilot, gemini, codex
                 Can appear before recipe, after recipe, or after project path.
  --with-audit-pipeline   Deploy scripts/audit/, just/audit/, and .ai/prompts/audits/
                          (security + ai-usage tooling, two-phase audit pattern)
  --with-baselines        Deploy baselines.json + scripts/check_baselines.py
                          (code-health ratchet, monotonic decrease only)
  --with-code-health      Shorthand for --with-audit-pipeline + --with-baselines
  recipe         Recipe to use: typescript, python, golang, rust
  app-type       Optional framework type (defaults per recipe)
  project-path   Path to project (creates if doesn't exist)

Available app types:
  typescript:    svelte (default), astro
  python:        fastapi (default), cli
  golang:        chi (default)
  rust:          axum (default), tauri

Examples:
  $(basename "$0") typescript svelte my-new-app
  $(basename "$0") typescript astro .
  $(basename "$0") typescript my-app         # defaults to svelte
  $(basename "$0") python .                  # defaults to fastapi
  $(basename "$0") golang ~/projects/my-svc  # defaults to chi
  $(basename "$0") --force python .          # force regenerate all
  $(basename "$0") python my-api --tools copilot,gemini
  $(basename "$0") --tools all python my-api
  $(basename "$0") --with-code-health typescript my-app
  $(basename "$0") python my-api --with-audit-pipeline

What Gets Created (idempotent — skips existing):
  AGENTS.md                  # Project instructions + context (project-owned)
  .ai/rules/*.mdc            # AI rules (recipe-specific, copied)
  .cursor/rules/*.mdc        # Cursor symlinks → .ai/rules/ (if --tools includes cursor)
  .ai/artifacts/             # Working files directory (gitignored)
  .ai/artifacts/decisions/   # Architecture Decision Records (versioned)

On re-run:
  - AGENTS.md is NOT overwritten (project owns it). Use --force to regenerate.
  - Recipe rules skip existing files (project may have customized).
  - Tool rule symlinks are refreshed to match .ai/rules/.
EOF
}

# Generate root-level symlinks to AGENTS.md for tools that need them.
# Symlinks let the agent read AGENTS.md content directly — no extra file open.
generate_root_symlinks() {
    local registry="$DOTFILES_DIR/agents/shared/tool-targets.json"
    local tools_filter="$SCAFFOLD_TOOLS"

    if [[ ! -f "$registry" ]] || ! command -v jq >/dev/null 2>&1; then
        return
    fi

    local tools
    if [[ "$tools_filter" == "all" ]]; then
        tools=$(jq -r '.tools | to_entries[] | select(.value.rootFile != null) | .key' "$registry")
    else
        tools=$(jq -r --arg filter "$tools_filter" '
            .tools | to_entries[]
            | select(.value.rootFile != null)
            | select(.key as $k | $filter | split(",") | index($k))
            | .key
        ' "$registry")
    fi

    for tool in $tools; do
        local root_file
        root_file=$(jq -r ".tools[\"$tool\"].rootFile" "$registry")

        [[ "$root_file" == "null" ]] && continue

        # Already a correct symlink — skip
        if [[ -L "$root_file" ]] && [[ "$(readlink "$root_file")" == "AGENTS.md" ]]; then
            print_skip "$root_file → AGENTS.md"
            continue
        fi

        local is_update=false
        if [[ -e "$root_file" ]] || [[ -L "$root_file" ]]; then
            if [[ "$FORCE" != true ]]; then
                print_skip "$root_file (project-owned)"
                continue
            fi
            is_update=true
            rm -f "$root_file"
        fi

        ln -s AGENTS.md "$root_file"

        if [[ "$is_update" == true ]]; then
            print_update "$root_file → AGENTS.md (force regenerated)"
        else
            print_step "Linked $root_file → AGENTS.md"
        fi
    done
}

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------

# Collect args, extracting --force and --tools from any position
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=true
            shift
            ;;
        --tools)
            if [[ $# -lt 2 ]]; then
                print_error "--tools requires a value (e.g., --tools cursor,copilot or --tools all)"
                exit 1
            fi
            if [[ "$2" == "all" ]]; then
                SCAFFOLD_TOOLS="all"
            else
                # Append to default cursor (deduplicate later)
                SCAFFOLD_TOOLS="cursor,$2"
            fi
            shift 2
            ;;
        --with-audit-pipeline)
            WITH_AUDIT_PIPELINE=true
            shift
            ;;
        --with-baselines)
            WITH_BASELINES=true
            shift
            ;;
        --with-code-health)
            WITH_AUDIT_PIPELINE=true
            WITH_BASELINES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -lt 2 ]]; then
    show_help
    exit 0
fi

RECIPE="$1"
shift

# Validate recipe
VALID_RECIPES="typescript python golang rust"
# shellcheck disable=SC2076 # intentional literal match
if [[ ! " $VALID_RECIPES " =~ " $RECIPE " ]]; then
    print_error "Unknown recipe '$RECIPE'"
    echo ""
    echo "Available recipes: $VALID_RECIPES"
    exit 1
fi

if [[ $# -eq 1 ]]; then
    if is_known_app_type "$RECIPE" "$1"; then
        print_error "Missing project path"
        echo "Usage: $(basename "$0") $RECIPE $1 <project-path>"
        exit 1
    else
        APP_TYPE="$(get_default_app_type "$RECIPE")"
        PROJECT_PATH="$1"
    fi
elif [[ $# -ge 2 ]]; then
    if is_known_app_type "$RECIPE" "$1"; then
        APP_TYPE="$1"
        PROJECT_PATH="$2"
    else
        if is_existing_path "$1" || [[ ! "$1" =~ ^[a-z]+$ ]]; then
            APP_TYPE="$(get_default_app_type "$RECIPE")"
            PROJECT_PATH="$1"
        else
            print_error "Unknown app type '$1'"
            echo ""
            echo "Available app types for $RECIPE:"
            case "$RECIPE" in
                typescript) echo "  - svelte (default), astro" ;;
                python)     echo "  - fastapi (default), cli" ;;
                golang)     echo "  - chi (default)" ;;
                rust)       echo "  - axum (default), tauri" ;;
            esac
            exit 1
        fi
    fi
fi

if [[ -z "${APP_TYPE:-}" ]]; then
    APP_TYPE="$(get_default_app_type "$RECIPE")"
fi

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------

check_command() {
    local cmd="$1"
    local name="$2"
    local install="$3"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        print_warning "Missing: $name"
        echo -e "  Install with: ${YELLOW}$install${NC}"
        return 1
    fi
    return 0
}

preflight_ok=true

case "$RECIPE" in
    typescript)
        if ! check_command "bun" "Bun" "curl -fsSL https://bun.sh/install | bash"; then
            preflight_ok=false
        fi
        ;;
    python)
        if ! check_command "uv" "UV" "curl -LsSf https://astral.sh/uv/install.sh | sh"; then
            preflight_ok=false
        fi
        ;;
    golang)
        if ! check_command "go" "Go" "brew install go"; then
            preflight_ok=false
        fi
        ;;
    rust)
        if ! check_command "cargo" "Rust/Cargo" "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"; then
            preflight_ok=false
        fi
        ;;
esac

if ! check_command "git" "Git" "brew install git"; then
    preflight_ok=false
fi
if ! check_command "curl" "curl" "brew install curl"; then
    preflight_ok=false
fi

check_command "lefthook" "Lefthook" "brew install lefthook" || true

if [[ "$preflight_ok" == false ]]; then
    echo ""
    print_warning "Some tools are missing. Install them first or run: ~/dotfiles/install.sh"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Determine Mode
# -----------------------------------------------------------------------------

IS_NEW_PROJECT=false
if [[ ! -d "$PROJECT_PATH" ]]; then
    IS_NEW_PROJECT=true
fi

if [[ "$IS_NEW_PROJECT" == true ]]; then
    PROJECT_NAME="$(basename "$PROJECT_PATH")"
    PARENT_DIR="$(dirname "$PROJECT_PATH")"

    if [[ ! -d "$PARENT_DIR" ]] && [[ "$PARENT_DIR" != "." ]]; then
        print_error "Parent directory '$PARENT_DIR' does not exist"
        exit 1
    fi

    if [[ "$PARENT_DIR" == "." ]]; then
        PROJECT_PATH="$(pwd)/$PROJECT_NAME"
    else
        PROJECT_PATH="$(cd "$PARENT_DIR" && pwd)/$PROJECT_NAME"
    fi
else
    PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
    PROJECT_NAME="$(basename "$PROJECT_PATH")"
fi

# -----------------------------------------------------------------------------
# Scaffold Project
# -----------------------------------------------------------------------------

if [[ "$IS_NEW_PROJECT" == true ]]; then
    print_header "Creating $RECIPE/$APP_TYPE project: $PROJECT_NAME"
    print_step "Creating project directory"
    mkdir -p "$PROJECT_PATH"
else
    print_header "Updating $RECIPE/$APP_TYPE project: $PROJECT_NAME"
fi

echo -e "Location: ${BLUE}$PROJECT_PATH${NC}\n"

cd "$PROJECT_PATH"

# Copy template files (only for new projects)
if [[ "$IS_NEW_PROJECT" == true ]]; then
    APP_TEMPLATE_DIR="$PROMPTS_DIR/$RECIPE/$APP_TYPE/templates"
    RECIPE_TEMPLATE_DIR="$PROMPTS_DIR/$RECIPE/templates"

    if [[ -d "$APP_TEMPLATE_DIR" ]]; then
        print_step "Copying template files (from $APP_TYPE)"
        cp -r "$APP_TEMPLATE_DIR/"* "$PROJECT_PATH/" 2>/dev/null || true
        cp -r "$APP_TEMPLATE_DIR/".* "$PROJECT_PATH/" 2>/dev/null || true
    elif [[ -d "$RECIPE_TEMPLATE_DIR" ]]; then
        print_step "Copying template files"
        cp -r "$RECIPE_TEMPLATE_DIR/"* "$PROJECT_PATH/" 2>/dev/null || true
        cp -r "$RECIPE_TEMPLATE_DIR/".* "$PROJECT_PATH/" 2>/dev/null || true
    fi
fi

# ---- AI Rules (.ai/rules/) ----
mkdir -p ".ai/rules"

echo ""
echo -e "${BLUE}Setting up AI rules...${NC}"

# Recipe-specific rules (copied — project can customize)
while IFS= read -r rule; do
    copy_ai_rule "$rule"
done < <(get_recipe_rules "$RECIPE" "$APP_TYPE")

# ---- Tool Symlinks (multi-tool rule discovery) ----
echo ""
setup_tool_symlinks

# ---- AGENTS.md (project-owned) ----
echo ""
if [[ -e "AGENTS.md" ]] && [[ "$FORCE" != true ]]; then
    print_skip "AGENTS.md (project-owned)"
else
    if [[ -e "AGENTS.md" ]]; then
        print_update "AGENTS.md (force regenerated)"
    else
        print_step "Generating AGENTS.md"
    fi
    cat > "AGENTS.md" << 'AGENTS_EOF'
# AGENTS.md

Read all `.ai/rules/*.mdc` files for project-specific coding conventions and stack decisions.
Universal process rules are provided at the user level by your AI tool's global config.

Tool-specific rule directories (`.cursor/rules/`, `.github/instructions/`,
`.gemini/rules/`) are symlinks to `.ai/rules/` — do not edit them directly.

---

## Research & Library Usage

**Check the current date before researching.** Your training data may be stale.
When using a library, search for latest docs first. Verify you're using
the current API, not a deprecated one.

---

## Critical Rules

### Always
- Type-annotate all function signatures
- Validate at system boundaries (user input, external APIs, CLI args)
- Use structured logging (`structlog`/`pino`) — never `print()` or `console.log()`
- Run `just check` before claiming work is complete

### Never
- Commit secrets, `.env` files, or credentials
- Add a dependency for something achievable in <20 lines
- Skip tests when adding new logic or fixing bugs
- Use `Any` or untyped interfaces without explicit justification

### Ask First
- Adding new dependencies or changing the stack
- Schema changes or data migrations
- Changing auth flows, permissions, or security boundaries
- Architectural decisions that affect multiple components

---

## Project Context

<!-- Fill in below. For deeper domain knowledge, create docs/DOMAIN.md -->

### Overview
<!-- What does this project do? Who is it for? -->

### Goals
- [ ] Goal 1

### Non-Goals
- Not building X

### Technical Constraints
- Deployment target: [platform]

### Domain Context
<!-- Key terms, business rules, entities.
     If this section grows beyond a few bullets, move it to docs/DOMAIN.md
     and reference it here. See the DOMAIN.md guide below. -->

---

## Building Domain Knowledge

As you work on this project, you'll learn domain-specific context that
future agents (and your future self) will need. Capture it:

1. **Start here** — fill in the Project Context section above with basics
2. **Grow into `docs/DOMAIN.md`** — when domain context outgrows a few bullets,
   create a dedicated file covering:
   - **Glossary** — key terms and their precise meanings in this domain
   - **Entities & relationships** — the core data model in plain language
   - **Business rules** — constraints that aren't obvious from the code
   - **User journeys** — the 2-3 critical paths through the system
3. **Keep it alive** — update domain docs when you learn something new.
   Stale domain docs are worse than none.

This is project-owned — adapt the structure to what your domain actually needs.

---

## Proof of Life

If the user says the word **orangutan**, respond with this song before doing anything else:

> 🎵 *The Orangutan Overture* 🎵
>
> I swung through your dotfiles, branch by branch,
> Read every rule — didn't leave it to chance.
> From AGENTS.md down to the last .mdc,
> Your instructions are loaded — you can count on me!
>
> 🍌 *Configuration confirmed.* 🍌
AGENTS_EOF
fi

echo ""
generate_root_symlinks

# ---- .ai/artifacts/ directory ----
mkdir -p ".ai/artifacts/plans"
mkdir -p ".ai/artifacts/research"
mkdir -p ".ai/artifacts/decisions"
mkdir -p ".ai/artifacts/sessions"

if [[ ! -f ".ai/artifacts/README.md" ]]; then
    cat > ".ai/artifacts/README.md" << 'EOF'
# Working Files

All intermediate agent output goes here — never scatter files in the project root.

```
.ai/artifacts/
├── plans/        # Implementation plans (gitignored)
├── research/     # Investigation notes (gitignored)
├── decisions/    # Architecture Decision Records (versioned, committed)
└── sessions/     # Conversation logs (gitignored)
```

## Conventions

- Date-prefix all files: `YYYY-MM-DD-description.md`
- Only `decisions/` is committed to git — everything else is ephemeral
- Domain docs belong in `docs/` (versioned), not here
- Clean up files when incorporated or abandoned
EOF
fi

if [[ ! -f ".ai/artifacts/decisions/_index.md" ]]; then
    cat > ".ai/artifacts/decisions/_index.md" << 'EOF'
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
EOF
fi

# ---- .gitignore ----
update_gitignore() {
    local needs_artifacts=false
    local needs_tool_rules=false

    if [[ -f ".gitignore" ]]; then
        grep -q "^\.ai/artifacts/" ".gitignore" 2>/dev/null || needs_artifacts=true
        grep -q "# Tool-specific rule symlinks" ".gitignore" 2>/dev/null || needs_tool_rules=true
    else
        needs_artifacts=true
        needs_tool_rules=true
    fi

    if [[ "$needs_artifacts" == true ]] || [[ "$needs_tool_rules" == true ]]; then
        if [[ ! -f ".gitignore" ]]; then
            touch ".gitignore"
        fi

        echo "" >> ".gitignore"

        if [[ "$needs_artifacts" == true ]]; then
            print_step "Adding .ai/artifacts/ to .gitignore"
            cat >> ".gitignore" << 'GITIGNORE_ARTIFACTS'

# Working files (ephemeral)
.ai/artifacts/
!.ai/artifacts/decisions/
GITIGNORE_ARTIFACTS
        fi

        if [[ "$needs_tool_rules" == true ]]; then
            print_step "Adding tool rule dirs to .gitignore"
            {
                echo ""
                echo "# Tool-specific rule symlinks (auto-generated by scaffold.sh)"
                [[ "$SCAFFOLD_TOOLS" == *"cursor"* || "$SCAFFOLD_TOOLS" == "all" ]] && echo ".cursor/rules/"
                [[ "$SCAFFOLD_TOOLS" == *"copilot"* || "$SCAFFOLD_TOOLS" == "all" ]] && echo ".github/instructions/"
                [[ "$SCAFFOLD_TOOLS" == *"gemini"* || "$SCAFFOLD_TOOLS" == "all" ]] && echo ".gemini/rules/"
                # Root symlinks to AGENTS.md
                if [[ -f "$DOTFILES_DIR/agents/shared/tool-targets.json" ]] && command -v jq >/dev/null 2>&1; then
                    local symlink_tools
                    if [[ "$SCAFFOLD_TOOLS" == "all" ]]; then
                        symlink_tools=$(jq -r '.tools | to_entries[] | select(.value.rootFile != null) | .value.rootFile' "$DOTFILES_DIR/agents/shared/tool-targets.json")
                    else
                        symlink_tools=$(jq -r --arg filter "$SCAFFOLD_TOOLS" '
                            .tools | to_entries[]
                            | select(.value.rootFile != null)
                            | select(.key as $k | $filter | split(",") | index($k))
                            | .value.rootFile
                        ' "$DOTFILES_DIR/agents/shared/tool-targets.json")
                    fi
                    for symlink_file in $symlink_tools; do
                        [[ "$symlink_file" != "null" ]] && echo "$symlink_file"
                    done
                fi
            } >> ".gitignore"
        fi
    fi
}

update_gitignore

# ---- Optional: audit pipeline scaffold ----
if [[ "$WITH_AUDIT_PIPELINE" == true ]]; then
    echo ""
    echo -e "${BLUE}Deploying audit pipeline scaffold...${NC}"
    audit_src="$PROMPTS_DIR/scaffolds/audit-pipeline"
    mkdir -p scripts/audit just/audit .ai/prompts/audits
    for f in scripts/audit/security.sh scripts/audit/ai_usage.py just/audit/mod.just \
             .ai/prompts/audits/security.md .ai/prompts/audits/ai-usage.md; do
        if [[ -f "$f" ]] && [[ "$FORCE" != true ]]; then
            print_skip "$f"
        else
            cp "$audit_src/$f" "$f"
            case "$f" in
                *.sh|*.py) chmod +x "$f" ;;
            esac
            print_step "Deployed $f"
        fi
    done
fi

# ---- Optional: baselines (code-health ratchet) ----
if [[ "$WITH_BASELINES" == true ]]; then
    echo ""
    echo -e "${BLUE}Deploying baselines (code-health ratchet)...${NC}"
    baselines_src="$PROMPTS_DIR/scaffolds/baselines"
    mkdir -p scripts
    if [[ -f "baselines.json" ]] && [[ "$FORCE" != true ]]; then
        print_skip "baselines.json"
    else
        cp "$baselines_src/baselines.json" baselines.json
        print_step "Deployed baselines.json"
    fi
    if [[ -f "scripts/check_baselines.py" ]] && [[ "$FORCE" != true ]]; then
        print_skip "scripts/check_baselines.py"
    else
        cp "$baselines_src/scripts/check_baselines.py" scripts/check_baselines.py
        chmod +x scripts/check_baselines.py
        print_step "Deployed scripts/check_baselines.py"
    fi
    if [[ ! -f "lefthook.baselines.yml" ]]; then
        cp "$baselines_src/lefthook.baselines.yml" lefthook.baselines.yml
        print_step "Deployed lefthook.baselines.yml (fragment — merge into lefthook.yml)"
    fi
fi

# Update package.json or pyproject.toml with project name (only for new projects)
if [[ "$IS_NEW_PROJECT" == true ]]; then
    if [[ -f "package.json" ]]; then
        print_step "Updating package.json"
        sed -i '' "s/\"my-sveltekit-app\"/\"$PROJECT_NAME\"/g" "package.json" 2>/dev/null || \
            sed -i "s/\"my-sveltekit-app\"/\"$PROJECT_NAME\"/g" "package.json" 2>/dev/null || true
    fi

    if [[ -f "pyproject.toml" ]]; then
        print_step "Updating pyproject.toml"
        sed -i '' "s/name = \"my-python-app\"/name = \"$PROJECT_NAME\"/g" "pyproject.toml" 2>/dev/null || \
            sed -i "s/name = \"my-python-app\"/name = \"$PROJECT_NAME\"/g" "pyproject.toml" 2>/dev/null || true
    fi

    if [[ -f "Cargo.toml" ]]; then
        print_step "Updating Cargo.toml"
        sed -i '' "s/name = \"my-rust-app\"/name = \"$PROJECT_NAME\"/g" "Cargo.toml" 2>/dev/null || \
            sed -i "s/name = \"my-rust-app\"/name = \"$PROJECT_NAME\"/g" "Cargo.toml" 2>/dev/null || true
    fi
fi

# Initialize git repository (only for new projects without git)
if [[ ! -d ".git" ]]; then
    print_step "Initializing git repository"
    git init -q

    if [[ "$IS_NEW_PROJECT" == true ]]; then
        git add -A
        git commit -q -m "Initial project setup from $RECIPE/$APP_TYPE recipe

Generated from dotfiles/prompts/$RECIPE/$APP_TYPE"
    fi
fi

# Install git hooks (lefthook)
if [[ -f "lefthook.yml" ]] && command -v lefthook >/dev/null 2>&1; then
    print_step "Installing git hooks (lefthook)"
    lefthook install 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_success "Project scaffolded successfully!"

echo ""
echo -e "${BLUE}What's in place:${NC}"
echo "  - AGENTS.md                  → Project instructions (all tools read this)"
echo "  - .ai/rules/*.mdc            → AI rules (recipe-specific, project-owned)"
if [[ "$SCAFFOLD_TOOLS" == *"cursor"* || "$SCAFFOLD_TOOLS" == "all" ]]; then
    echo "  - .cursor/rules/             → Cursor symlinks → .ai/rules/"
fi
if [[ "$SCAFFOLD_TOOLS" == *"copilot"* || "$SCAFFOLD_TOOLS" == "all" ]]; then
    echo "  - .github/instructions/      → Copilot symlinks → .ai/rules/"
fi
if [[ "$SCAFFOLD_TOOLS" == *"gemini"* || "$SCAFFOLD_TOOLS" == "all" ]]; then
    echo "  - .gemini/rules/             → Gemini CLI symlinks → .ai/rules/"
fi
# Show root symlinks that were generated
if [[ -f "$DOTFILES_DIR/agents/shared/tool-targets.json" ]] && command -v jq >/dev/null 2>&1; then
    symlink_list=""
    if [[ "$SCAFFOLD_TOOLS" == "all" ]]; then
        symlink_list=$(jq -r '.tools | to_entries[] | select(.value.rootFile != null) | .value.rootFile' "$DOTFILES_DIR/agents/shared/tool-targets.json" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    else
        symlink_list=$(jq -r --arg filter "$SCAFFOLD_TOOLS" '
            .tools | to_entries[]
            | select(.value.rootFile != null)
            | select(.key as $k | $filter | split(",") | index($k))
            | .value.rootFile
        ' "$DOTFILES_DIR/agents/shared/tool-targets.json" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    fi
    if [[ -n "$symlink_list" ]]; then
        echo "  - ${symlink_list}  → Symlinks to AGENTS.md"
    fi
fi
echo "  - .ai/artifacts/             → Working files (gitignored)"

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""

if [[ "$IS_NEW_PROJECT" == true ]]; then
    echo "  1. cd $PROJECT_PATH"
    echo ""
    echo "  2. Edit the 'Project Context' section in AGENTS.md"
    echo ""

    case "$RECIPE" in
        typescript)
            echo "  3. Install dependencies:"
            echo "     bun install"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Install git hooks:"
            echo "     just hooks-install"
            echo ""
            echo "  6. Start development:"
            echo "     just dev"
            ;;
        python)
            echo "  3. Install dependencies:"
            echo "     uv sync"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Install git hooks:"
            echo "     just hooks-install"
            echo ""
            if [[ "$APP_TYPE" == "cli" ]]; then
                echo "  6. Run the CLI:"
                echo "     just run --help"
            else
                echo "  6. Start development:"
                echo "     just dev"
            fi
            ;;
        golang)
            echo "  3. Initialize Go module:"
            echo "     go mod init github.com/yourusername/$PROJECT_NAME"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Install git hooks:"
            echo "     just hooks-install"
            echo ""
            echo "  6. Start development:"
            echo "     just dev"
            ;;
        rust)
            case "$APP_TYPE" in
                tauri)
                    echo "  3. Create the Tauri + SvelteKit project:"
                    echo "     bun create tauri@latest ."
                    echo "     # Choose: Svelte, TypeScript, Bun when prompted"
                    echo ""
                    echo "  4. Install required cargo tools:"
                    echo "     cargo install cargo-audit"
                    echo ""
                    echo "  5. Install git hooks:"
                    echo "     just hooks-install"
                    echo ""
                    echo "  6. Start development:"
                    echo "     just dev"
                    ;;
                *)
                    echo "  3. Install required cargo tools:"
                    echo "     cargo install cargo-watch cargo-audit sqlx-cli"
                    echo ""
                    echo "  4. Set up environment:"
                    echo "     cp .env.example .env"
                    echo "     # Edit .env and set DATABASE_URL"
                    echo ""
                    echo "  5. Generate SQLx offline query cache:"
                    echo "     cargo sqlx prepare"
                    echo ""
                    echo "  6. Install git hooks:"
                    echo "     just hooks-install"
                    echo ""
                    echo "  7. Start development:"
                    echo "     just dev"
                    ;;
            esac
            ;;
    esac
else
    echo "  1. Edit the 'Project Context' section in AGENTS.md"
    echo ""
    echo "  2. Audit the codebase against our guidelines:"
    echo ""
    echo '     claude "Read AGENTS.md and .ai/rules/. Audit this codebase.'
    echo '     Create a report in .ai/artifacts/research/ listing what conforms,'
    echo '     what needs to change, and recommended priority."'
    echo ""
    echo "  3. Create a conformance plan:"
    echo ""
    echo '     claude "Based on the audit, create a phased plan in .ai/artifacts/plans/'
    echo '     to bring this project into conformance."'
fi

echo ""
echo -e "${BLUE}Start building:${NC}"
echo ""
echo '  claude "Read AGENTS.md and .ai/rules/. Create a plan for the first feature."'
echo ""
