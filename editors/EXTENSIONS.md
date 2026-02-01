# Editor Extensions

Curated extension list optimized for **SvelteKit + Python** development.

## Current Extension List

### Universal / Productivity
- **better-comments** - Color-coded comments for better readability
- **code-spell-checker** - Spell checking in code
- **todo-tree** - Highlight and manage TODO comments
- **vscode-icons** - File type icons
- **errorlens** - Inline error/warning highlighting (best-in-class DX)

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

### TypeScript / SvelteKit (Best-in-Class DX)
- **svelte.svelte-vscode** - Svelte/SvelteKit language support
- **eslint** - JavaScript/TypeScript linting (fallback for non-Biome projects)
- **prettier-vscode** - Code formatter (fallback for non-Biome projects)
- **biomejs.biome** - Fast linter/formatter (preferred over ESLint+Prettier)
- **playwright** - E2E testing support

### HTML & CSS / Tailwind
- **tailwindcss** - Tailwind CSS IntelliSense
- **tailwind-fold** - Collapse long Tailwind class lists
- **auto-rename-tag** - Auto-rename paired HTML tags

## Extension Selection Rationale

### Python Stack
- **Ruff** chosen over flake8/pylint for speed (10-100x faster)
- **Pylance** (included with python extension) provides fast type checking
- **debugpy** for seamless debugging experience
- **Marimo** - Modern reactive notebooks (Git-friendly .py files)

### SvelteKit Stack
- **Svelte extension** - Essential for .svelte file support
- **Biome** preferred over ESLint+Prettier (35x faster, single tool)
- **Playwright** - Modern E2E testing
- **Tailwind IntelliSense** - Essential for Tailwind-heavy projects
- **Error Lens** - Makes TypeScript errors immediately visible

### Why These Extensions?
1. **Error Lens** - Shows errors inline, reducing context switching
2. **Ruff** - Fastest Python linter (written in Rust)
3. **Biome** - Fastest JS/TS linter (written in Rust, replaces ESLint+Prettier)
4. **Pylance** - Fast type checking with excellent IntelliSense
5. **GitLens** - Essential for understanding code history

## Notes

- **Biome vs ESLint+Prettier**: New projects should use Biome. ESLint+Prettier are kept for legacy projects.
- For project-specific AI rules, see `prompts/*/AGENTS.md` rather than editor-level config.
