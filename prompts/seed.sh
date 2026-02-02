#!/usr/bin/env bash
# =============================================================================
# Recipe Seed Script (for existing projects)
# =============================================================================
# Adds project organization structure to an existing project without
# overwriting existing files or initializing git.
#
# Usage:
#   ./prompts/seed.sh <recipe> <project-path>
#
# Examples:
#   ./prompts/seed.sh typescript /path/to/my-existing-app
#   ./prompts/seed.sh python .
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

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

show_help() {
    cat << EOF
Recipe Seed Script (for existing projects)

Usage:
  $(basename "$0") <recipe> <project-path>

Arguments:
  recipe         Recipe to use: typescript, python, golang
  project-path   Path to existing project (use . for current directory)

Examples:
  $(basename "$0") typescript /path/to/my-app
  $(basename "$0") python .
  $(basename "$0") golang ~/projects/my-service

What Gets Added (won't overwrite existing files):
  AGENTS.md           # Symlinked from recipe
  ABSTRACT.md    # Template for you to fill in
  .agents/            # Working files directory
  .architecture/         # Architecture decisions directory

This script is safe to run multiple times - it won't overwrite existing files.
EOF
}

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

# Check arguments
if [[ $# -lt 2 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
    exit 0
fi

RECIPE="$1"
PROJECT_PATH="$2"

# Resolve to absolute path
PROJECT_PATH="$(cd "$PROJECT_PATH" 2>/dev/null && pwd)" || {
    print_error "Directory '$2' does not exist"
    exit 1
}

# Validate recipe exists
RECIPE_DIR="$PROMPTS_DIR/$RECIPE"
if [[ ! -d "$RECIPE_DIR" ]]; then
    print_error "Recipe '$RECIPE' not found"
    echo ""
    echo "Available recipes:"
    for dir in "$PROMPTS_DIR"/*/; do
        if [[ -f "$dir/AGENTS.md" ]]; then
            echo "  - $(basename "$dir")"
        fi
    done
    exit 1
fi

# Validate recipe has required files
if [[ ! -f "$RECIPE_DIR/AGENTS.md" ]]; then
    print_error "Recipe '$RECIPE' is missing AGENTS.md"
    exit 1
fi

# -----------------------------------------------------------------------------
# Seed Project
# -----------------------------------------------------------------------------

print_header "Seeding existing project with $RECIPE recipe"
echo -e "Project: ${BLUE}$PROJECT_PATH${NC}\n"

cd "$PROJECT_PATH"

# Symlink AGENTS.md (or skip if exists)
if [[ -e "AGENTS.md" ]]; then
    print_skip "AGENTS.md"
else
    print_step "Symlinking AGENTS.md"
    ln -s "$RECIPE_DIR/AGENTS.md" "AGENTS.md"
fi

# Copy ABSTRACT.md (or skip if exists)
if [[ -e "ABSTRACT.md" ]]; then
    print_skip "ABSTRACT.md"
else
    print_step "Creating ABSTRACT.md template"
    cp "$PROMPTS_DIR/templates/ABSTRACT.md" "ABSTRACT.md"
    # Try to extract project name from directory
    PROJECT_NAME="$(basename "$PROJECT_PATH")"
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

    # Create README
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

    # Create README
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

    # Create ADR index
    cat > ".architecture/adr/_index.md" << 'EOF'
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
EOF
fi

# Check if .agents is in .gitignore
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

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_success "Project seeded successfully!"

echo ""
echo -e "${BLUE}What was added:${NC}"
echo "  - AGENTS.md        → Instructions for AI coding agents"
echo "  - ABSTRACT.md → Your project description (edit this!)"
echo "  - .agents/         → Working files (gitignored)"
echo "  - .architecture/      → Architecture decisions (versioned)"

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
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
echo ""
echo "  4. Execute incrementally:"
echo ""
echo '     claude "Execute phase 1 of the conformance plan. Run tests after'
echo '     each change to verify nothing broke."'
echo ""
