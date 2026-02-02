#!/usr/bin/env bash
# =============================================================================
# Project Scaffold Script
# =============================================================================
# Creates or updates a project with dotfiles recipe structure.
# Safe to run multiple times — idempotent.
#
# Usage:
#   ./prompts/scaffold.sh <recipe> [app-type] <project-path>
#
# Examples:
#   ./prompts/scaffold.sh typescript svelte my-new-app    # Creates new project
#   ./prompts/scaffold.sh typescript svelte .             # Seeds current dir
#   ./prompts/scaffold.sh typescript my-app               # Defaults to svelte
#   ./prompts/scaffold.sh python .                        # Defaults to fastapi
#   ./prompts/scaffold.sh golang chi ~/projects/my-svc
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

# Get default app type for a recipe
get_default_app_type() {
    local recipe="$1"
    case "$recipe" in
        typescript) echo "svelte" ;;
        python) echo "fastapi" ;;
        golang) echo "chi" ;;
        *) echo "" ;;
    esac
}

# Check if an argument is a valid app type for a recipe
is_valid_app_type() {
    local recipe="$1"
    local app_type="$2"
    local app_dir="$PROMPTS_DIR/$recipe/$app_type"
    [[ -d "$app_dir" && -f "$app_dir/FRAMEWORK.md" ]]
}

# Check if path looks like an existing directory or current dir
is_existing_path() {
    local path="$1"
    [[ "$path" == "." ]] || [[ -d "$path" ]]
}

# List available app types for a recipe
list_app_types() {
    local recipe="$1"
    for dir in "$PROMPTS_DIR/$recipe"/*/; do
        if [[ -f "$dir/FRAMEWORK.md" ]]; then
            basename "$dir"
        fi
    done
}

show_help() {
    cat << EOF
Project Scaffold Script

Creates or updates a project with dotfiles recipe structure.
Safe to run multiple times — only adds missing pieces.

Usage:
  $(basename "$0") <recipe> [app-type] <project-path>

Arguments:
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

What Gets Created (idempotent — skips existing):
  AGENTS.md           # Combined base + framework instructions
  ABSTRACT.md         # Template for you to fill in
  .agents/            # Working files directory (gitignored)
  .architecture/      # Architecture decisions directory

If AGENTS.md exists, it will be regenerated to pick up any recipe updates.
EOF
}

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------

if [[ $# -lt 2 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
    exit 0
fi

RECIPE="$1"
shift

# Validate recipe exists
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

# Parse remaining arguments: [app-type] <project-path>
if [[ $# -eq 1 ]]; then
    # Single arg — could be app-type (need path) or path (use default app-type)
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
        # First arg isn't a valid app type
        # Could be: unknown app type, or project-path with extra args
        if is_existing_path "$1" || [[ ! "$1" =~ ^[a-z]+$ ]]; then
            # Looks like a path, use default app type
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

# Validate app type
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

# Validate base recipe has required files
if [[ ! -f "$RECIPE_DIR/BASE.md" ]]; then
    print_error "Recipe '$RECIPE' is missing BASE.md"
    exit 1
fi

# -----------------------------------------------------------------------------
# Determine Mode: New Project vs Seed Existing
# -----------------------------------------------------------------------------

IS_NEW_PROJECT=false
if [[ ! -d "$PROJECT_PATH" ]]; then
    IS_NEW_PROJECT=true
fi

# Resolve or create project path
if [[ "$IS_NEW_PROJECT" == true ]]; then
    # Get parent directory and project name
    PROJECT_NAME="$(basename "$PROJECT_PATH")"
    PARENT_DIR="$(dirname "$PROJECT_PATH")"

    # Ensure parent exists
    if [[ ! -d "$PARENT_DIR" ]] && [[ "$PARENT_DIR" != "." ]]; then
        print_error "Parent directory '$PARENT_DIR' does not exist"
        exit 1
    fi

    # Resolve to absolute path (parent must exist)
    if [[ "$PARENT_DIR" == "." ]]; then
        PROJECT_PATH="$(pwd)/$PROJECT_NAME"
    else
        PROJECT_PATH="$(cd "$PARENT_DIR" && pwd)/$PROJECT_NAME"
    fi
else
    # Existing directory — resolve to absolute
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

# Copy template files (only for new projects, from app-type specific or recipe templates)
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

# Generate AGENTS.md (always regenerate to pick up recipe updates)
if [[ -e "AGENTS.md" ]]; then
    print_update "AGENTS.md (regenerated from $RECIPE/$APP_TYPE)"
else
    print_step "Generating AGENTS.md (base + $APP_TYPE)"
fi
{
    cat "$RECIPE_DIR/BASE.md"
    echo ""
    echo "---"
    echo ""
    cat "$APP_DIR/FRAMEWORK.md"
} > "AGENTS.md"

# Create ABSTRACT.md (skip if exists)
if [[ -e "ABSTRACT.md" ]]; then
    print_skip "ABSTRACT.md"
else
    print_step "Creating ABSTRACT.md template"
    cp "$PROMPTS_DIR/templates/ABSTRACT.md" "ABSTRACT.md"
    sed -i '' "s/\[Project Name\]/$PROJECT_NAME/g" "ABSTRACT.md" 2>/dev/null || \
        sed -i "s/\[Project Name\]/$PROJECT_NAME/g" "ABSTRACT.md" 2>/dev/null || true
fi

# Create .agents directory structure
if [[ -d ".agents" ]]; then
    print_skip ".agents/"
else
    print_step "Creating .agents/ directory"
    mkdir -p ".agents/plans"
    mkdir -p ".agents/research"
    mkdir -p ".agents/prompts"
    mkdir -p ".agents/sessions"

    cat > ".agents/README.md" << 'EOF'
# Working Files (Layer 3)

This directory contains ephemeral agent-generated artifacts. Gitignored by default.

## Structure

```
.agents/
├── plans/      # Implementation plans
├── research/   # Investigation notes
├── prompts/    # Key prompts that led to decisions
└── sessions/   # Conversation logs
```

## Naming Convention

Use date-prefixed names: `YYYY-MM-DD-description.md`

---

**Note**: Architecture decisions go in `.architecture/adr/`, not here.
EOF
fi

# Create .architecture directory structure
if [[ -d ".architecture" ]]; then
    print_skip ".architecture/"
else
    print_step "Creating .architecture/ directory"
    mkdir -p ".architecture/adr"

    cat > ".architecture/README.md" << 'EOF'
# Decision History (Layer 2)

This directory contains versioned Architecture Decision Records (ADRs).

## Structure

```
.architecture/
├── adr/           # Architecture Decision Records
│   └── 0001-*.md  # Numbered ADRs
└── CHANGELOG.md   # Timeline of decisions
```

## Attribution Tags

- 👤 HUMAN: Human made this call
- 🤖 AI-SUGGESTED: AI proposed, human approved
- 🤖→👤 AI-REFINED: AI explored, human decided
- ⚠️ ASSUMED: Nobody explicitly decided (validate this)
EOF

    cat > ".architecture/adr/_index.md" << 'EOF'
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
EOF
fi

# Ensure .agents/ is in .gitignore
if [[ -f ".gitignore" ]]; then
    if ! grep -q "^\.agents/" ".gitignore" 2>/dev/null; then
        print_step "Adding .agents/ to .gitignore"
        echo "" >> ".gitignore"
        echo "# Working files (ephemeral)" >> ".gitignore"
        echo ".agents/" >> ".gitignore"
    fi
else
    print_step "Creating .gitignore with .agents/"
    echo "# Working files (ephemeral)" > ".gitignore"
    echo ".agents/" >> ".gitignore"
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

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_success "Project scaffolded successfully!"

echo ""
echo -e "${BLUE}What's in place:${NC}"
echo "  - AGENTS.md        → Instructions for AI coding agents ($RECIPE + $APP_TYPE)"
echo "  - ABSTRACT.md      → Your project description (edit this!)"
echo "  - .agents/         → Working files (gitignored)"
echo "  - .architecture/   → Architecture decisions (versioned)"

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""

if [[ "$IS_NEW_PROJECT" == true ]]; then
    echo "  1. cd $PROJECT_PATH"
    echo ""
    echo "  2. Edit ABSTRACT.md to describe what you're building"
    echo ""

    case "$RECIPE" in
        typescript)
            echo "  3. Install dependencies:"
            echo "     bun install"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Start development:"
            echo "     just dev"
            ;;
        python)
            echo "  3. Install dependencies:"
            echo "     uv sync"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Start development:"
            echo "     just dev"
            ;;
        golang)
            echo "  3. Initialize Go module:"
            echo "     go mod init github.com/yourusername/$PROJECT_NAME"
            echo ""
            echo "  4. Set up environment:"
            echo "     cp .env.example .env"
            echo ""
            echo "  5. Start development:"
            echo "     just dev"
            ;;
    esac
else
    echo "  1. Edit ABSTRACT.md to describe your project"
    echo ""
    echo "  2. Audit the codebase against our guidelines:"
    echo ""
    echo '     claude "Read AGENTS.md and audit this codebase. Create a report in'
    echo '     .agents/research/ listing what conforms, what needs to change, and'
    echo '     recommended priority. Don'\''t make changes yet."'
    echo ""
    echo "  3. Create a conformance plan:"
    echo ""
    echo '     claude "Based on the audit, create a phased plan in .agents/plans/'
    echo '     to bring this project into conformance. Each phase should be safe'
    echo '     and incremental."'
fi

echo ""
echo -e "${BLUE}Start building with Claude Code:${NC}"
echo ""
echo '  claude "Read AGENTS.md and ABSTRACT.md. Create a plan for the first feature."'
echo ""
