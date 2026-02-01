# Editor Extensions

Curated extension list optimized for **SvelteKit + Python** development.

## Current Extension List

### Universal / Productivity
- **better-comments** - Color-coded comments for better readability
- **code-spell-checker** - Spell checking in code
- **todo-tree** - Highlight and manage TODO comments
- **vscode-icons** - File type icons
- **errorlens** - Inline error/warning highlighting (best-in-class DX)
- **path-intellisense** - Autocomplete file paths in imports

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

### ML / Data Science
- **jupyter** - Jupyter notebook support
- **vscode-tensorboard** - TensorBoard integration

### TypeScript / SvelteKit (Best-in-Class DX)
- **svelte.svelte-vscode** - Svelte/SvelteKit language support
- **biomejs.biome** - Fast linter/formatter (preferred over ESLint+Prettier)
- **vscode-eslint** - ESLint (fallback for legacy projects)
- **prettier-vscode** - Prettier (fallback for legacy projects)
- **playwright** - E2E testing support
- **pretty-ts-errors** - Human-readable TypeScript errors

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
- **Pretty TS Errors** - Makes TypeScript error messages actually readable
- **Playwright** - Modern E2E testing
- **Tailwind IntelliSense** - Essential for Tailwind-heavy projects
- **Error Lens** - Makes TypeScript errors immediately visible

### Why These Extensions?
1. **Error Lens** - Shows errors inline, reducing context switching
2. **Ruff** - Fastest Python linter (written in Rust)
3. **Biome** - Fastest JS/TS linter (written in Rust, replaces ESLint+Prettier)
4. **Pretty TS Errors** - Makes TS errors human-readable instead of cryptic
5. **Path Intellisense** - Autocomplete import paths, saves time
6. **GitLens** - Essential for understanding code history

## Settings Highlights

The settings files (`vscode/settings.json`, `cursor/settings.json`) include:

- **Tab size 2** - Matches our TypeScript/Svelte style
- **Format on save** - Automatic code formatting
- **Biome as default** for JS/TS/Svelte files
- **Ruff as default** for Python files (with auto-fix on save)
- **CVA/cn() support** for Tailwind (shadcn-svelte compatible)
- **Sticky scroll** - Keep function/class headers visible
- **Bracket colorization** - Easier to match brackets

## Notes

- **Biome vs ESLint+Prettier**: New projects should use Biome. ESLint+Prettier are kept for legacy projects.
- For project-specific AI rules, see `prompts/*/AGENTS.md` rather than editor-level config.
- Settings are kept in sync between VS Code and Cursor.
