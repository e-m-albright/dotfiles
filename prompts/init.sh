#!/usr/bin/env bash
# =============================================================================
# Recipe Initialization Script
# =============================================================================
# Creates a new project from a dotfiles recipe
#
# Usage:
#   ./prompts/init.sh <recipe> <project-name> [destination]
#
# Examples:
#   ./prompts/init.sh typescript my-web-app
#   ./prompts/init.sh python my-api ~/projects
#   ./prompts/init.sh golang my-service .
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
Recipe Initialization Script

Usage:
  $(basename "$0") <recipe> <project-name> [destination]

Arguments:
  recipe         Recipe to use: typescript, python, golang
  project-name   Name of the new project (used for directory)
  destination    Parent directory (default: current directory)

Examples:
  $(basename "$0") typescript my-web-app
  $(basename "$0") python my-api ~/projects
  $(basename "$0") golang my-service

Available Recipes:
  typescript     Bun + SvelteKit 2 + Svelte 5 + Tailwind v4 + Drizzle
  python         UV + FastAPI + Pydantic v2 + SQLAlchemy 2.0
  golang         Go 1.22+ stdlib + sqlc + pgx

What Gets Created:
  <project-name>/
  ├── AGENTS.md           # Symlinked from recipe (for AI agents)
  ├── PROJECT_BRIEF.md    # Template for you to fill in
  ├── .agents/            # Working files (gitignored)
  │   └── plans/, research/, prompts/, sessions/
  ├── .architecture/         # Architecture decisions (versioned)
  │   └── adr/, README.md
  ├── .gitignore          # Copied from recipe
  ├── justfile            # Copied from recipe
  └── [other templates]   # Recipe-specific files
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
PROJECT_NAME="$2"
DESTINATION="${3:-.}"

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

if [[ ! -d "$RECIPE_DIR/templates" ]]; then
    print_error "Recipe '$RECIPE' is missing templates/ directory"
    exit 1
fi

# Create full project path
PROJECT_PATH="$DESTINATION/$PROJECT_NAME"

# Check if project already exists
if [[ -d "$PROJECT_PATH" ]]; then
    print_error "Directory '$PROJECT_PATH' already exists"
    exit 1
fi

# -----------------------------------------------------------------------------
# Initialize Project
# -----------------------------------------------------------------------------

print_header "Initializing $RECIPE project: $PROJECT_NAME"

# Create project directory
print_step "Creating project directory"
mkdir -p "$PROJECT_PATH"

# Copy template files
print_step "Copying template files"
cp -r "$RECIPE_DIR/templates/"* "$PROJECT_PATH/" 2>/dev/null || true
cp -r "$RECIPE_DIR/templates/".* "$PROJECT_PATH/" 2>/dev/null || true

# Symlink AGENTS.md
print_step "Symlinking AGENTS.md"
ln -s "$RECIPE_DIR/AGENTS.md" "$PROJECT_PATH/AGENTS.md"

# Create .agents directory (Layer 3: Working Context)
print_step "Creating .agents/ directory"
mkdir -p "$PROJECT_PATH/.agents/plans"
mkdir -p "$PROJECT_PATH/.agents/research"
mkdir -p "$PROJECT_PATH/.agents/prompts"
mkdir -p "$PROJECT_PATH/.agents/sessions"

# Create .architecture directory (Layer 2: Decision History)
print_step "Creating .architecture/ directory"
mkdir -p "$PROJECT_PATH/.architecture/adr"

# Create .agents/README.md
cat > "$PROJECT_PATH/.agents/README.md" << 'EOF'
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

## Index

<!-- Agent should update this section when creating files -->

### Plans

(none yet)

### Research

(none yet)

---

**Note**: Architecture decisions go in `.architecture/adr/`, not here.
See `prompts/shared/PROJECT_MEMORY.md` for the full three-layer system.
EOF

# Create .architecture/README.md
cat > "$PROJECT_PATH/.architecture/README.md" << 'EOF'
# Decision History (Layer 2)

This directory contains versioned Architecture Decision Records (ADRs).

## Structure

```
.architecture/
├── adr/           # Architecture Decision Records
│   └── 0001-*.md  # Numbered ADRs
└── CHANGELOG.md   # Timeline of decisions
```

## Creating an ADR

```bash
# Create a new ADR
touch .architecture/adr/0001-your-decision.md
```

Use the template from `prompts/shared/PROJECT_MEMORY.md`.

## Attribution Tags

- 👤 HUMAN: Human made this call
- 🤖 AI-SUGGESTED: AI proposed, human approved
- 🤖→👤 AI-REFINED: AI explored, human decided
- ⚠️ ASSUMED: Nobody explicitly decided (validate this)
EOF

# Create .architecture/adr/_index.md
cat > "$PROJECT_PATH/.architecture/adr/_index.md" << 'EOF'
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
EOF

# Copy PROJECT_BRIEF.md template
print_step "Creating PROJECT_BRIEF.md template"
cp "$PROMPTS_DIR/templates/PROJECT_BRIEF.md" "$PROJECT_PATH/PROJECT_BRIEF.md"

# Update PROJECT_BRIEF.md with project name
sed -i '' "s/\[Project Name\]/$PROJECT_NAME/g" "$PROJECT_PATH/PROJECT_BRIEF.md" 2>/dev/null || \
    sed -i "s/\[Project Name\]/$PROJECT_NAME/g" "$PROJECT_PATH/PROJECT_BRIEF.md" 2>/dev/null || true

# Update package.json or similar with project name (if exists)
if [[ -f "$PROJECT_PATH/package.json" ]]; then
    print_step "Updating package.json"
    sed -i '' "s/\"my-sveltekit-app\"/\"$PROJECT_NAME\"/g" "$PROJECT_PATH/package.json" 2>/dev/null || \
        sed -i "s/\"my-sveltekit-app\"/\"$PROJECT_NAME\"/g" "$PROJECT_PATH/package.json" 2>/dev/null || true
fi

if [[ -f "$PROJECT_PATH/pyproject.toml" ]]; then
    print_step "Updating pyproject.toml"
    sed -i '' "s/name = \"my-python-app\"/name = \"$PROJECT_NAME\"/g" "$PROJECT_PATH/pyproject.toml" 2>/dev/null || \
        sed -i "s/name = \"my-python-app\"/name = \"$PROJECT_NAME\"/g" "$PROJECT_PATH/pyproject.toml" 2>/dev/null || true
fi

# Initialize git repository
print_step "Initializing git repository"
cd "$PROJECT_PATH"
git init -q

# Create initial commit
git add -A
git commit -q -m "Initial project setup from $RECIPE recipe

Generated from dotfiles/prompts/$RECIPE"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_success "Project created successfully!"

echo ""
echo -e "${BLUE}Project location:${NC} $PROJECT_PATH"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. cd $PROJECT_PATH"
echo ""
echo "  2. Edit PROJECT_BRIEF.md to describe what you're building"
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

echo ""
echo -e "${BLUE}Project structure:${NC}"
echo "  - AGENTS.md        → Instructions for AI coding agents"
echo "  - PROJECT_BRIEF.md → Your project description (edit this!)"
echo "  - .agents/         → Working files (gitignored)"
echo "  - .architecture/      → Architecture decisions (versioned)"
echo ""
echo -e "${BLUE}Start building with Claude Code:${NC}"
echo ""
echo '  claude "Read AGENTS.md and PROJECT_BRIEF.md. Create a plan for the first feature."'
echo ""
