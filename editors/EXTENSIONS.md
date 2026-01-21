# Editor Extensions

Curated extension list optimized for **Python + Next.js** development.

## Current Extension List

### Universal / Productivity
- **better-comments** - Color-coded comments for better readability
- **code-spell-checker** - Spell checking in code
- **todo-tree** - Highlight and manage TODO comments
- **vscode-icons** - File type icons
- **errorlens** - Inline error/warning highlighting (best-in-class DX) ⭐

### Version Control
- **gitlens** - Git supercharged (blame, history, annotations)

### Files
- **even-better-toml** - Enhanced TOML file support

### Docker
- **vscode-docker** - Docker container management

### Python (Best-in-Class DX)
- **python** - Python language support + Pylance (fast type checking)
- **debugpy** - Python debugging support
- **ruff** - Fast Python linter/formatter (replaces flake8/pylint/black)
- **marimo** - Reactive Python notebooks (alternative to Jupyter, stores as .py files)
- **marimo** - Reactive Python notebooks (alternative to Jupyter, stores as .py files)

### Next.js / React / TypeScript (Best-in-Class DX)
- **eslint** - JavaScript/TypeScript linting
- **prettier-vscode** - Code formatter (works with ESLint)
- **jsdoc-generator** - JSDoc comment generation
- **playwright** - E2E testing support for Next.js

### HTML & CSS / Tailwind
- **tailwindcss** - Tailwind CSS IntelliSense
- **tailwind-fold** - Collapse long Tailwind class lists
- **auto-rename-tag** - Auto-rename paired HTML tags

## Extension Selection Rationale

### Python Stack
- **Ruff** chosen over flake8/pylint for speed (10-100x faster)
- **Pylance** (included with python extension) provides fast type checking
- **debugpy** for seamless debugging experience
- **Marimo** - Modern reactive notebooks (Git-friendly .py files, better than Jupyter for many workflows)

### Next.js Stack
- **ESLint + Prettier** - Industry standard for React/Next.js
- **Playwright** - Modern E2E testing (better than Cypress for Next.js)
- **Tailwind IntelliSense** - Essential for Tailwind-heavy projects
- **Error Lens** - Makes TypeScript/ESLint errors immediately visible

### Why These Extensions?
1. **Error Lens** - Shows errors inline, reducing context switching
2. **Ruff** - Fastest Python linter (written in Rust)
3. **Pylance** - Fast type checking with excellent IntelliSense
4. **Playwright** - Best E2E testing for Next.js (official recommendation)
5. **GitLens** - Essential for understanding code history

## Future Considerations

- **EditorConfig** - Currently commented; uncomment if working across multiple projects
- **Thunder Client** - REST API client (alternative to Postman)
- **Jupyter** - If doing data science/ML work
