#!/usr/bin/env bash
# =============================================================================
# Project Scaffold Script
# =============================================================================
# Creates or updates a project with cross-vendor AI rules.
# Safe to run multiple times — idempotent.
#
# Philosophy: Dotfiles seeds and influences. Projects own themselves.
# - All .ai/rules/ are COPIED (project owns them, re-run --force to update)
# - .cursor/rules/ gets relative symlinks to .ai/rules/ for Cursor
# - AGENTS.md is GENERATED once, then project-owned (never overwritten)
#
# Usage:
#   ./prompts/scaffold.sh <recipe> [app-type] <project-path>
#   ./prompts/scaffold.sh --force <recipe> [app-type] <project-path>
#
# Examples:
#   ./prompts/scaffold.sh typescript svelte my-new-app
#   ./prompts/scaffold.sh typescript svelte .
#   ./prompts/scaffold.sh typescript my-app               # Defaults to svelte
#   ./prompts/scaffold.sh python .                        # Defaults to fastapi
#   ./prompts/scaffold.sh golang chi ~/projects/my-svc
#   ./prompts/scaffold.sh --force python .                # Force regenerate all
# =============================================================================

set -euo pipefail

# Get script directory (where dotfiles/prompts lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AI_RULES_DIR="$DOTFILES_DIR/.ai/rules"

FORCE=false

# Source shared print functions
source "$DOTFILES_DIR/macos/print_utils.sh"

# =============================================================================
# Universal rules (copied — re-run with --force to update)
# =============================================================================
UNIVERSAL_RULES=(
    "process/global-process.mdc"
    "process/style-principles.mdc"
    "process/github-workflow.mdc"
    "process/tickets-and-prs.mdc"
    "process/agent-artifacts.mdc"
)

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
        typescript/svelte|typescript/astro|python/fastapi|golang/chi|rust/axum|rust/tauri)
            return 0 ;;
        *)
            return 1 ;;
    esac
}

is_existing_path() {
    local path="$1"
    [[ "$path" == "." ]] || [[ -d "$path" ]]
}

# Copy a universal rule file into .ai/rules/ (re-copied on --force or re-scaffold)
# Previously symlinked; now copied so projects don't depend on dotfiles path.
# To update rules across projects: re-run scaffold.sh --force in each project.
copy_universal_rule() {
    local rule_path="$1"  # e.g., "process/global-process.mdc"
    local rule_name
    rule_name="$(basename "$rule_path")"
    local source="$AI_RULES_DIR/$rule_path"
    local dest=".ai/rules/$rule_name"

    if [[ ! -f "$source" ]]; then
        print_warning "Rule not found in dotfiles: $rule_path"
        return
    fi

    # If it's a stale symlink from old scaffold, replace it
    if [[ -L "$dest" ]]; then
        rm "$dest"
    fi

    # Check if content is already up to date
    if [[ -f "$dest" ]] && diff -q "$source" "$dest" >/dev/null 2>&1; then
        print_skip ".ai/rules/$rule_name"
        return
    fi

    if [[ -f "$dest" ]] && [[ "$FORCE" != true ]]; then
        print_skip ".ai/rules/$rule_name (project-owned, differs from dotfiles)"
        return
    fi

    cp "$source" "$dest"
    print_step "Copied .ai/rules/$rule_name"
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
    if [[ "$FORCE" == true ]]; then
        print_update ".ai/rules/$rule_name (force copied)"
    else
        print_step "Copied .ai/rules/$rule_name"
    fi
}

# Create relative symlinks in .cursor/rules/ → .ai/rules/ for Cursor discovery
setup_cursor_symlinks() {
    mkdir -p ".cursor/rules"

    for rule_file in .ai/rules/*.mdc; do
        [[ -f "$rule_file" ]] || continue
        local rule_name
        rule_name="$(basename "$rule_file")"
        local cursor_link=".cursor/rules/$rule_name"

        if [[ -L "$cursor_link" ]]; then
            # Already a symlink — update if target changed
            local current_target
            current_target="$(readlink "$cursor_link")"
            if [[ "$current_target" == "../../.ai/rules/$rule_name" ]]; then
                continue
            fi
            rm "$cursor_link"
        elif [[ -f "$cursor_link" ]] && [[ "$FORCE" != true ]]; then
            continue
        fi

        ln -s "../../.ai/rules/$rule_name" "$cursor_link"
    done
    print_step "Cursor symlinks created (.cursor/rules/ → .ai/rules/)"
}

show_help() {
    cat << EOF
Project Scaffold Script

Creates or updates a project with cross-vendor AI rules.
Safe to run multiple times — only adds missing pieces.

Usage:
  $(basename "$0") [--force] <recipe> [app-type] <project-path>

Arguments:
  --force        Force regenerate AGENTS.md and overwrite existing rules
  recipe         Recipe to use: typescript, python, golang, rust
  app-type       Optional framework type (defaults per recipe)
  project-path   Path to project (creates if doesn't exist)

Available app types:
  typescript:    svelte (default), astro
  python:        fastapi (default)
  golang:        chi (default)
  rust:          axum (default), tauri

Examples:
  $(basename "$0") typescript svelte my-new-app
  $(basename "$0") typescript astro .
  $(basename "$0") typescript my-app         # defaults to svelte
  $(basename "$0") python .                  # defaults to fastapi
  $(basename "$0") golang ~/projects/my-svc  # defaults to chi
  $(basename "$0") --force python .          # force regenerate all

What Gets Created (idempotent — skips existing):
  AGENTS.md              # Project instructions + context (project-owned)
  .ai/rules/*.mdc        # AI rules (universal=symlinked, recipe=copied)
  .cursor/rules/*.mdc    # Cursor symlinks → .ai/rules/ (auto-generated)
  .agents/               # Working files directory (gitignored)
  .agents/decisions/     # Architecture Decision Records (versioned)

On re-run:
  - AGENTS.md is NOT overwritten (project owns it). Use --force to regenerate.
  - Universal rules are re-symlinked (always up to date).
  - Recipe rules skip existing files (project may have customized).
  - .cursor/rules/ symlinks are refreshed to match .ai/rules/.
EOF
}

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------

if [[ $# -ge 1 ]] && [[ "$1" == "--force" ]]; then
    FORCE=true
    shift
fi

if [[ $# -lt 2 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
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
                python)     echo "  - fastapi (default)" ;;
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

# Universal rules (copied — re-run scaffold.sh --force to update)
for rule in "${UNIVERSAL_RULES[@]}"; do
    copy_universal_rule "$rule"
done

# Recipe-specific rules (copied — project can customize)
while IFS= read -r rule; do
    copy_ai_rule "$rule"
done < <(get_recipe_rules "$RECIPE" "$APP_TYPE")

# ---- Cursor Symlinks (.cursor/rules/ → .ai/rules/) ----
echo ""
setup_cursor_symlinks

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

Read all `.ai/rules/*.mdc` files for coding conventions, stack decisions,
and process rules. Cursor users: rules are also in `.cursor/rules/`.

---

## Research & Library Usage

**Check the current date before researching.** Your training data may be stale.
When using a library, search for latest docs first. Verify you're using
the current API, not a deprecated one.

---

## Project Context

<!-- Fill this in -->

### Overview
<!-- What does this project do? Who is it for? -->

### Goals
- [ ] Goal 1

### Non-Goals
- Not building X

### Technical Constraints
- Deployment target: [platform]

### Domain Context
<!-- Key terms, business rules, entities -->
AGENTS_EOF
fi

# ---- .agents/ directory ----
mkdir -p ".agents/plans"
mkdir -p ".agents/research"
mkdir -p ".agents/decisions"
mkdir -p ".agents/sessions"

if [[ ! -f ".agents/README.md" ]]; then
    cat > ".agents/README.md" << 'EOF'
# Working Files

Agent-generated artifacts: plans, research, and sessions are gitignored.
Architecture decisions in `decisions/` are versioned.

```
.agents/
├── plans/        # Implementation plans
├── research/     # Investigation notes
├── decisions/    # Architecture Decision Records (versioned)
└── sessions/     # Conversation logs
```

Use date-prefixed names: `YYYY-MM-DD-description.md`
EOF
fi

if [[ ! -f ".agents/decisions/_index.md" ]]; then
    cat > ".agents/decisions/_index.md" << 'EOF'
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
EOF
fi

# ---- .gitignore ----
update_gitignore() {
    local needs_agents=false
    local needs_ai_rules=false
    local needs_cursor_rules=false

    if [[ -f ".gitignore" ]]; then
        grep -q "^\.agents/" ".gitignore" 2>/dev/null || needs_agents=true
        grep -q "^\.ai/rules/global-process" ".gitignore" 2>/dev/null || needs_ai_rules=true
        grep -q "^\.cursor/rules/" ".gitignore" 2>/dev/null || needs_cursor_rules=true
    else
        needs_agents=true
        needs_ai_rules=true
        needs_cursor_rules=true
    fi

    if [[ "$needs_agents" == true ]] || [[ "$needs_ai_rules" == true ]] || [[ "$needs_cursor_rules" == true ]]; then
        if [[ ! -f ".gitignore" ]]; then
            touch ".gitignore"
        fi

        echo "" >> ".gitignore"

        if [[ "$needs_agents" == true ]]; then
            print_step "Adding .agents/ to .gitignore"
            cat >> ".gitignore" << 'GITIGNORE_AGENTS'

# Working files (ephemeral)
.agents/
!.agents/decisions/
GITIGNORE_AGENTS
        fi

        if [[ "$needs_ai_rules" == true ]]; then
            print_step "Adding symlinked .ai/rules/ to .gitignore"
            cat >> ".gitignore" << 'GITIGNORE_AI'

# .ai/rules/ — symlinked process rules are machine-specific
.ai/rules/global-process.mdc
.ai/rules/style-principles.mdc
.ai/rules/github-workflow.mdc
.ai/rules/tickets-and-prs.mdc
.ai/rules/agent-artifacts.mdc
# Recipe-specific rules are committed (they're copies, not symlinks)
GITIGNORE_AI
        fi

        if [[ "$needs_cursor_rules" == true ]]; then
            print_step "Adding .cursor/rules/ to .gitignore"
            cat >> ".gitignore" << 'GITIGNORE_CURSOR'

# .cursor/rules/ — auto-generated symlinks to .ai/rules/
.cursor/rules/
GITIGNORE_CURSOR
        fi
    fi
}

update_gitignore

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
    lefthook install -q 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_success "Project scaffolded successfully!"

echo ""
echo -e "${BLUE}What's in place:${NC}"
echo "  - AGENTS.md              → Project instructions + context (you own this)"
echo "  - .ai/rules/*.mdc        → AI rules (universal=symlinked, recipe=copied)"
echo "  - .cursor/rules/*.mdc    → Cursor symlinks (auto-generated)"
echo "  - .agents/               → Working files (gitignored)"
echo "  - .agents/decisions/     → Architecture decisions (versioned)"

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
            echo "  6. Start development:"
            echo "     just dev"
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
    echo '     Create a report in .agents/research/ listing what conforms,'
    echo '     what needs to change, and recommended priority."'
    echo ""
    echo "  3. Create a conformance plan:"
    echo ""
    echo '     claude "Based on the audit, create a phased plan in .agents/plans/'
    echo '     to bring this project into conformance."'
fi

echo ""
echo -e "${BLUE}Start building:${NC}"
echo ""
echo '  claude "Read AGENTS.md and .ai/rules/. Create a plan for the first feature."'
echo ""
