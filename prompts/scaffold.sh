#!/usr/bin/env bash
# =============================================================================
# Project Scaffold Script
# =============================================================================
# Creates or updates a project with dotfiles recipe structure.
# Safe to run multiple times — idempotent.
#
# Philosophy: Dotfiles seeds and influences. Projects own themselves.
# - Universal .cursor/rules/ are SYMLINKED (auto-update from dotfiles)
# - Recipe-specific .cursor/rules/ are COPIED (project can customize)
# - AGENTS.md is GENERATED once, then project-owned (never overwritten)
# - Re-running refreshes rules but respects project customizations
#
# Usage:
#   ./prompts/scaffold.sh <recipe> [app-type] <project-path>
#   ./prompts/scaffold.sh --force <recipe> [app-type] <project-path>
#
# Examples:
#   ./prompts/scaffold.sh typescript svelte my-new-app    # Creates new project
#   ./prompts/scaffold.sh typescript svelte .             # Seeds current dir
#   ./prompts/scaffold.sh typescript my-app               # Defaults to svelte
#   ./prompts/scaffold.sh python .                        # Defaults to fastapi
#   ./prompts/scaffold.sh golang chi ~/projects/my-svc
#   ./prompts/scaffold.sh --force python .                # Force regenerate all
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory (where dotfiles/prompts lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RULES_DIR="$DOTFILES_DIR/.cursor/rules"

FORCE=false

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_step() {
    echo -e "${GREEN}→${NC} $1"
}

print_skip() {
    echo -e "${YELLOW}○${NC} $1 (already exists)"
}

print_update() {
    echo -e "${YELLOW}↻${NC} $1 (updated)"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

get_default_app_type() {
    local recipe="$1"
    case "$recipe" in
        typescript) echo "svelte" ;;
        python) echo "fastapi" ;;
        golang) echo "chi" ;;
        *) echo "" ;;
    esac
}

is_valid_app_type() {
    local recipe="$1"
    local app_type="$2"
    local app_dir="$PROMPTS_DIR/$recipe/$app_type"
    [[ -d "$app_dir" && -f "$app_dir/FRAMEWORK.md" ]]
}

is_existing_path() {
    local path="$1"
    [[ "$path" == "." ]] || [[ -d "$path" ]]
}

list_app_types() {
    local recipe="$1"
    for dir in "$PROMPTS_DIR/$recipe"/*/; do
        if [[ -f "$dir/FRAMEWORK.md" ]]; then
            basename "$dir"
        fi
    done
}

# Symlink a rule file (universal rules — auto-update from dotfiles)
symlink_rule() {
    local rule_name="$1"
    local target="$RULES_DIR/$rule_name"
    local link=".cursor/rules/$rule_name"

    if [[ ! -f "$target" ]]; then
        print_warning "Rule not found in dotfiles: $rule_name"
        return
    fi

    if [[ -L "$link" ]]; then
        local current_target
        current_target="$(readlink "$link")"
        if [[ "$current_target" == "$target" ]]; then
            print_skip ".cursor/rules/$rule_name (symlink)"
            return
        fi
        rm "$link"
        print_update ".cursor/rules/$rule_name (symlink updated)"
    elif [[ -f "$link" ]] && [[ "$FORCE" != true ]]; then
        print_skip ".cursor/rules/$rule_name (project-owned)"
        return
    fi

    ln -s "$target" "$link"
    print_step "Symlinked .cursor/rules/$rule_name"
}

# Copy a rule file (recipe-specific — project can customize)
copy_rule() {
    local rule_name="$1"
    local source="$RULES_DIR/$rule_name"

    if [[ ! -f "$source" ]]; then
        print_warning "Rule not found in dotfiles: $rule_name"
        return
    fi

    if [[ -f ".cursor/rules/$rule_name" ]] && [[ "$FORCE" != true ]]; then
        print_skip ".cursor/rules/$rule_name"
        return
    fi

    cp "$source" ".cursor/rules/$rule_name"
    if [[ "$FORCE" == true ]] && [[ -f ".cursor/rules/$rule_name" ]]; then
        print_update ".cursor/rules/$rule_name (force copied)"
    else
        print_step "Copied .cursor/rules/$rule_name"
    fi
}

show_help() {
    cat << EOF
Project Scaffold Script

Creates or updates a project with dotfiles recipe structure.
Safe to run multiple times — only adds missing pieces.

Usage:
  $(basename "$0") [--force] <recipe> [app-type] <project-path>

Arguments:
  --force        Force regenerate AGENTS.md and overwrite existing rules
  recipe         Recipe to use: typescript, python, golang
  app-type       Optional framework type (defaults per recipe)
  project-path   Path to project (creates if doesn't exist)

Available app types:
  typescript:    svelte (default), astro
  python:        fastapi (default)
  golang:        chi (default)

Examples:
  $(basename "$0") typescript svelte my-new-app
  $(basename "$0") typescript astro .
  $(basename "$0") typescript my-app         # defaults to svelte
  $(basename "$0") python .                  # defaults to fastapi
  $(basename "$0") golang ~/projects/my-svc  # defaults to chi
  $(basename "$0") --force python .          # force regenerate all

What Gets Created (idempotent — skips existing):
  AGENTS.md              # Project instructions + context (project-owned)
  .cursor/rules/*.mdc    # Cursor rules (universal=symlinked, recipe=copied)
  .agents/               # Working files directory (gitignored)
  .agents/decisions/     # Architecture Decision Records (versioned)

On re-run:
  - AGENTS.md is NOT overwritten (project owns it). Use --force to regenerate.
  - Universal rules are re-symlinked (always up to date).
  - Recipe rules skip existing files (project may have customized).
  - .agents/ is created if missing, decisions/ ensured.
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

RECIPE_DIR="$PROMPTS_DIR/$RECIPE"
if [[ ! -d "$RECIPE_DIR" ]]; then
    print_error "Recipe '$RECIPE' not found"
    echo ""
    echo "Available recipes:"
    for dir in "$PROMPTS_DIR"/*/; do
        if [[ -f "$dir/BASE.md" ]]; then
            echo "  - $(basename "$dir")"
        fi
    done
    exit 1
fi

if [[ $# -eq 1 ]]; then
    if is_valid_app_type "$RECIPE" "$1"; then
        print_error "Missing project path"
        echo "Usage: $(basename "$0") $RECIPE $1 <project-path>"
        exit 1
    else
        APP_TYPE="$(get_default_app_type "$RECIPE")"
        PROJECT_PATH="$1"
    fi
elif [[ $# -ge 2 ]]; then
    if is_valid_app_type "$RECIPE" "$1"; then
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
            list_app_types "$RECIPE" | while read -r t; do echo "  - $t"; done
            exit 1
        fi
    fi
fi

if [[ -z "$APP_TYPE" ]]; then
    print_error "No app types available for recipe '$RECIPE'"
    exit 1
fi

APP_DIR="$RECIPE_DIR/$APP_TYPE"
if [[ ! -d "$APP_DIR" ]] || [[ ! -f "$APP_DIR/FRAMEWORK.md" ]]; then
    print_error "App type '$APP_TYPE' not found for recipe '$RECIPE'"
    echo ""
    echo "Available app types for $RECIPE:"
    list_app_types "$RECIPE" | while read -r t; do echo "  - $t"; done
    exit 1
fi

if [[ ! -f "$RECIPE_DIR/BASE.md" ]]; then
    print_error "Recipe '$RECIPE' is missing BASE.md"
    exit 1
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
esac

if ! check_command "git" "Git" "brew install git"; then
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
    if [[ -d "$APP_DIR/templates" ]]; then
        print_step "Copying template files (from $APP_TYPE)"
        cp -r "$APP_DIR/templates/"* "$PROJECT_PATH/" 2>/dev/null || true
        cp -r "$APP_DIR/templates/".* "$PROJECT_PATH/" 2>/dev/null || true
    elif [[ -d "$RECIPE_DIR/templates" ]]; then
        print_step "Copying template files"
        cp -r "$RECIPE_DIR/templates/"* "$PROJECT_PATH/" 2>/dev/null || true
        cp -r "$RECIPE_DIR/templates/".* "$PROJECT_PATH/" 2>/dev/null || true
    fi
fi

# ---- Cursor Rules ----
mkdir -p ".cursor/rules"

# Universal rules (symlinked — auto-update from dotfiles)
symlink_rule "global-process.mdc"
symlink_rule "tickets-and-prs.mdc"
symlink_rule "agent-artifacts.mdc"
symlink_rule "github-workflow.mdc"

# Recipe-specific rules (copied — project can customize)
case "$RECIPE" in
    python)
        copy_rule "python-uv-ruff.mdc"
        copy_rule "shell-automation.mdc"
        ;;
    typescript)
        copy_rule "javascript-typescript.mdc"
        ;;
    golang)
        copy_rule "golang.mdc"
        copy_rule "shell-automation.mdc"
        ;;
esac

# ---- AGENTS.md (project-owned) ----
if [[ -e "AGENTS.md" ]] && [[ "$FORCE" != true ]]; then
    print_skip "AGENTS.md (project-owned)"
else
    if [[ -e "AGENTS.md" ]]; then
        print_update "AGENTS.md (force regenerated from $RECIPE/$APP_TYPE)"
    else
        print_step "Generating AGENTS.md (base + $APP_TYPE)"
    fi
    {
        cat << HEADER
# AGENTS.md

Read all \`.cursor/rules/*.mdc\` files for process, safety, and coding conventions.

---

## Project Context

<!-- Fill this in to describe YOUR project. Delete sections that don't apply. -->

### Overview

<!-- What does this project do? What problem does it solve? Who is it for? -->

### Goals

- [ ] Goal 1
- [ ] Goal 2

### Non-Goals

- Not building X
- Not supporting Y

### Technical Constraints

- Deployment target: [platform]
- Must work with: [existing systems]

### Domain Context

<!-- Key terms, business rules, entities, and relationships -->

---

## Code Patterns

HEADER
        cat "$RECIPE_DIR/BASE.md"
        echo ""
        echo "---"
        echo ""
        cat "$APP_DIR/FRAMEWORK.md"
    } > "AGENTS.md"

    sed -i '' "s/\[Project Name\]/$PROJECT_NAME/g" "AGENTS.md" 2>/dev/null || \
        sed -i "s/\[Project Name\]/$PROJECT_NAME/g" "AGENTS.md" 2>/dev/null || true
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
if [[ -f ".gitignore" ]]; then
    if ! grep -q "^\.agents/" ".gitignore" 2>/dev/null; then
        print_step "Adding .agents/ to .gitignore"
        echo "" >> ".gitignore"
        echo "# Working files (ephemeral)" >> ".gitignore"
        echo ".agents/" >> ".gitignore"
        echo "!.agents/decisions/" >> ".gitignore"
    fi
else
    if [[ -f "$RECIPE_DIR/templates/.gitignore" ]]; then
        print_step "Creating .gitignore (from template)"
        cp "$RECIPE_DIR/templates/.gitignore" ".gitignore"
    else
        print_step "Creating .gitignore"
        echo "# Working files (ephemeral)" > ".gitignore"
        echo ".agents/" >> ".gitignore"
        echo "!.agents/decisions/" >> ".gitignore"
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
echo "  - .cursor/rules/*.mdc    → Cursor rules (universal=symlinked, recipe=copied)"
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
    esac
else
    echo "  1. Edit the 'Project Context' section in AGENTS.md"
    echo ""
    echo "  2. Audit the codebase against our guidelines:"
    echo ""
    echo '     claude "Read AGENTS.md and .cursor/rules/. Audit this codebase.'
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
echo '  claude "Read AGENTS.md and .cursor/rules/. Create a plan for the first feature."'
echo ""
