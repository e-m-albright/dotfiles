---
name: scaffold-project
description: Scaffold a new project (or update an existing one) with cross-vendor AI rules, templates, and directory structure using dotfiles recipes. Use when user invokes /scaffold-project, says "scaffold a new app/project/repo", "set up a fresh repo with rules", "bootstrap a project"; or names a recipe (`typescript`, `python`, `golang`, `rust`) plus a target directory.
disable-model-invocation: true
---

# Scaffold Project

Scaffold a new project (or update an existing one) with cross-vendor AI rules, templates, and directory structure.

## Usage

`/scaffold-project <recipe> [app-type] <project-path>`

## Arguments

- `recipe` — Language recipe: `typescript`, `python`, `golang`, `rust`
- `app-type` — Optional framework (defaults per recipe):
  - typescript: `svelte` (default), `astro`
  - python: `fastapi` (default), `cli`
  - golang: `chi` (default)
  - rust: `axum` (default), `tauri`
- `project-path` — Target directory (created if it doesn't exist, `.` for current)

Add `--force` before the recipe to regenerate AGENTS.md and overwrite existing rules.

## Workflow

1. Parse the user's arguments into recipe, app-type, and project-path
2. Run the scaffold command:

```bash
dotfiles scaffold [--force] <recipe> [app-type] <project-path>
```

3. Report what was created or updated
4. If this is a new project, remind the user to fill in the "Project Context" section of AGENTS.md

## Examples

```
/scaffold-project typescript svelte ~/code/my-app
/scaffold-project python .
/scaffold-project --force golang chi ~/code/my-api
```
