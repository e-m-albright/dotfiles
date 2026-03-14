# Agentic Parity: Unified Claude Code + Cursor Setup

**Date**: 2026-03-14
**Status**: Approved design, pending implementation

## Problem

Claude Code and Cursor are both agentic coding tools but their configs diverged:

- **MCP servers**: Claude Code has 4, Cursor has 2, only Linear overlaps
- **Rules**: Claude Code auto-deploys `~/.claude/CLAUDE.md`; Cursor requires manual paste from `USER_RULES.md`
- **Skills/Agents**: Claude Code has skills + agents; Cursor's are disabled
- **Hooks**: Claude Code has 4 hook events; Cursor has none
- **Permissions**: Cursor CLI uses legacy format (`read.files`) vs modern (`Shell(git)`)
- **Deploy**: `dotfiles install` is all-or-nothing; `dotfiles doctor` is read-only; no lightweight fix path
- **Visibility**: No way to see what's active across both tools

The directory structure reflects the drift: `claude/` sits at root while Cursor is nested under `editors/cursor/`, mixing editor settings with agentic config.

## Design

### 1. Directory Restructure

Separate **agentic behavior** (how tools think and act) from **editor settings** (how tools look and format):

```
agents/                          # Agentic behavior
├── shared/                      # Common base for all agentic tools
│   ├── mcp-servers.json         # Superset of MCP servers with per-tool targeting
│   ├── rules.md                 # Shared guardrails (both tools consume)
│   └── ignore-patterns          # Shared context exclusions
├── claude/                      # Claude Code agent config
│   ├── setup.sh                 # Deploys to ~/.claude/ and ~/.claude.json
│   ├── global-claude.md         # Claude-specific wrapper around shared/rules.md
│   ├── hooks.json               # PreToolUse guard, PostToolUse format, notifications
│   ├── hooks/
│   │   └── format-on-save.sh    # Multi-language formatter + shellcheck
│   ├── plugins.yaml             # Plugin list
│   ├── marketplaces.json        # Community marketplace registrations
│   ├── desktop-preferences.json # Claude Desktop prefs
│   ├── skills/
│   │   ├── scaffold-project/SKILL.md
│   │   ├── dotfiles-doctor/SKILL.md
│   │   └── agents-overview/SKILL.md
│   └── agents/
│       └── shellcheck-reviewer.md
├── cursor/                      # Cursor agent config (IS a Cursor plugin)
│   ├── .cursor-plugin/
│   │   └── plugin.json          # Plugin manifest
│   ├── setup.sh                 # Registers plugin + deploys config
│   ├── cli-config.json          # Modern permission format
│   ├── .mcp.json                # Generated from shared/mcp-servers.json
│   ├── rules/
│   │   └── shared-rules.mdc    # Generated from shared/rules.md
│   ├── skills/
│   │   ├── scaffold-project/SKILL.md
│   │   └── dotfiles-doctor/SKILL.md
│   ├── agents/
│   │   └── shellcheck-reviewer.md
│   └── hooks/
│       ├── hooks.json           # afterFileEdit, beforeShellExecution
│       ├── format-on-save-shim.sh  # Normalizes Cursor stdin → shared format
│       └── guard-destructive.sh    # Blocks destructive shell commands
└── overview.sh                  # Engine for `dotfiles agents` command

editors/                         # Editor settings (non-agentic)
├── cursor/
│   ├── settings.json            # Themes, formatters, UI prefs
│   ├── extensions.sh            # Extension installer
│   └── .cursorignore            # Context exclusions (augmented from shared/)
├── obsidian/                    # Knowledge base configs
├── extensions.sh                # Shared extension installer
└── EXTENSIONS.md
```

**Migration**: `claude/` moves to `agents/claude/`. Agentic parts of `editors/cursor/` move to `agents/cursor/`. Editor parts stay in `editors/cursor/`. All paths in `install.sh`, `bin/dotfiles`, and `CLAUDE.md` updated.

### 2. Shared Config Layer (`agents/shared/`)

#### `mcp-servers.json`

Single source of truth. Each server has a `targets` array controlling which tools receive it:

```json
{
  "github": {
    "command": "gh",
    "args": ["mcp-server"],
    "targets": ["claude", "cursor"]
  },
  "linear": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "https://mcp.linear.app/mcp"],
    "targets": ["claude", "cursor"]
  },
  "granola": {
    "command": "uvx",
    "args": ["granola-mcp"],
    "targets": ["claude"]
  },
  "notion": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "https://mcp.notion.com/mcp"],
    "targets": ["claude", "cursor"]
  },
  "context7": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp@latest"],
    "targets": ["cursor"]
  }
}
```

Each tool's `setup.sh` reads this file, filters by target, strips the `targets` field, and writes the standard `{"mcpServers": {...}}` format to the tool's deploy location.

Claude Desktop receives the same MCP servers as Claude Code (all entries targeting `"claude"`). The `agents/claude/setup.sh` handles both `~/.claude.json` and `~/Library/Application Support/Claude/claude_desktop_config.json` as it does today.

Context7 targets cursor-only because Claude Code gets it via the context7 plugin (which provides richer integration than raw MCP).

#### `rules.md`

Merged from current `global-claude.md` + `USER_RULES.md`, deduplicated:

```markdown
# Shared Agentic Rules

## Process
- Verify before claiming done — run tests/builds and show output. Evidence before assertions.
- Brainstorm before building — confirm requirements and approach for non-trivial features.
- Plan multi-step work — write a brief plan for tasks with 3+ steps.
- TDD when testing exists — write/update tests before implementation.
- Debug systematically — reproduce, hypothesize, test. No shotgun fixes.

## Safety
- Never commit secrets or .env files.
- Never run destructive git operations unless explicitly asked.
- Minimize surface area — smallest change that solves the request.
- Respect existing conventions (formatter, linter, package manager, hook system).

## Context
- Detect stack and tooling from existing project files before proposing commands.
- Check the current date before researching libraries. Search for latest docs first.
- Prefer existing project scripts/task runners over introducing new ones.
- If assumptions are required, state them briefly and proceed with safest default.

## Testing
- Generate or update tests when adding new logic, refactoring, or fixing bugs.
- For tests/format/lint, run only what is relevant to changed files unless asked for full suite.
```

**Claude Code**: `global-claude.md` imports this content and adds Claude-specific sections (command style preferences for dedicated tools, worktree instructions, heredoc commits).

**Cursor**: `setup.sh` generates `rules/shared-rules.mdc` with frontmatter (`alwaysApply: true`, description) wrapping this content.

#### `ignore-patterns`

Plain text, one pattern per line. Common context exclusions:

```
node_modules/
.next/
dist/
build/
coverage/
.env
.env.*
*.log
*.min.js
*.min.css
__pycache__/
.pytest_cache/
```

Cursor's `.cursorignore` is generated from this plus Cursor-specific patterns. Claude Code respects `.gitignore` by default so this primarily informs the overview report.

### 3. Cursor Plugin (`agents/cursor/`)

The `agents/cursor/` directory is itself a Cursor plugin. It contains `.cursor-plugin/plugin.json` at its root, and Cursor auto-discovers skills, agents, rules, hooks, and MCP servers from the standard directory names.

#### Plugin Manifest (`.cursor-plugin/plugin.json`)

```json
{
  "name": "dotfiles",
  "description": "Personal agentic config — rules, skills, agents, hooks",
  "version": "1.0.0",
  "author": { "name": "evan" }
}
```

#### `setup.sh`

Responsibilities:
1. Filter `agents/shared/mcp-servers.json` for `targets: ["cursor"]` and write `.mcp.json`
2. Generate `rules/shared-rules.mdc` from `agents/shared/rules.md` with frontmatter
3. Register this directory as a local plugin by writing an entry to `~/.cursor/extensions/extensions.json` (the plugin registry) with a `dotfiles@local` key and absolute `installPath` pointing to this directory. Enable third-party plugins in Cursor Settings > Features if not already on. The exact registry format should be verified during implementation by inspecting an existing local plugin installation.
4. Deploy `cli-config.json` to `~/.cursor/cli-config.json`
5. Generate `editors/cursor/.cursorignore` from `agents/shared/ignore-patterns` plus Cursor-specific additions

Generated files (`.mcp.json`, `rules/shared-rules.mdc`) are added to `.gitignore` since they're derived from `agents/shared/` and would drift if committed.

#### `cli-config.json` (updated)

Rewritten with modern permission syntax:

```json
{
  "version": 1,
  "editor": { "vimMode": false },
  "permissions": {
    "allow": [
      "Shell(git)",
      "Shell(npm)",
      "Shell(bun)",
      "Shell(go)",
      "Shell(cargo)",
      "Shell(just)",
      "Shell(dotfiles)",
      "Shell(shellcheck)",
      "Shell(lefthook)",
      "Read(**)",
      "Write(src/**)",
      "Write(tests/**)",
      "Write(*.md)"
    ],
    "deny": [
      "Shell(rm -rf /)",
      "Shell(sudo)",
      "Write(.env)",
      "Write(.env.*)",
      "Write(**/credentials*)",
      "Write(**/*id_rsa*)",
      "Write(**/*id_ed25519*)"
    ]
  },
  "attribution": {
    "attributeCommitsToAgent": true,
    "attributePRsToAgent": true
  }
}
```

#### Skills

Mirror Claude Code's skills, adapted for Cursor's tool names:

- `scaffold-project/SKILL.md` — same content, calls `~/dotfiles/prompts/scaffold.sh`
- `dotfiles-doctor/SKILL.md` — same content, calls `~/dotfiles/bin/dotfiles doctor`

#### Agents

- `shellcheck-reviewer.md` — same content, portable (uses `find` + `shellcheck`, no Claude-specific tools)

#### Hooks (`hooks/hooks.json`)

```json
{
  "hooks": [
    {
      "event": "afterFileEdit",
      "command": "~/dotfiles/agents/claude/hooks/format-on-save.sh",
      "matcher": "*.sh|*.ts|*.tsx|*.js|*.jsx|*.py|*.rs|*.go|*.json"
    },
    {
      "event": "beforeShellExecution",
      "command": "~/dotfiles/agents/cursor/hooks/guard-destructive.sh",
      "matcher": "*"
    }
  ]
}
```

The format-on-save hook is NOT directly shared. Cursor's `afterFileEdit` stdin format may differ from Claude Code's `PostToolUse` format. The Cursor hook calls a shim script (`agents/cursor/hooks/format-on-save-shim.sh`) that normalizes the input to match the `{"tool_input": {"file_path": "..."}}` shape before calling the shared formatter logic. During implementation, verify the actual Cursor hook stdin schema and adjust the shim accordingly.

### 4. `dotfiles agents` Command + Claude Code Skill

#### `agents/overview.sh`

Reads deployed state from:
- `~/.claude/settings.json` (Claude Code hooks, plugins)
- `~/.claude.json` (Claude Code MCP servers)
- `~/.cursor/mcp.json` or deployed plugin `.mcp.json` (Cursor MCP)
- `~/.cursor/plugins/` (Cursor plugins, skills, agents)
- `~/.claude/skills/`, `~/.claude/agents/` (Claude Code skills, agents)

Compares against source config in `agents/` and reports:

| Section | What it shows |
|---------|---------------|
| MCP Servers | Per-server: which tools have it, source (shared/plugin/cloud), drift warnings |
| Hooks | Per-event: what each tool does, any gaps |
| Skills | Per-skill: availability in each tool, invocation mode |
| Agents | Per-agent: availability in each tool |
| Rules | Source file, where deployed for each tool |
| Permissions | Count per tool, format warnings |

Drift detection: if deployed state doesn't match source config, show a warning with `dotfiles doctor --fix` suggestion.

#### CLI integration (`bin/dotfiles`)

New subcommand:

```bash
sub_agents() {
    "$DOTFILES_DIR/agents/overview.sh" "$@"
}
```

Added to help text, completions, and case statement.

#### Claude Code skill (`agents/claude/skills/agents-overview/SKILL.md`)

```yaml
---
name: agents-overview
description: Show active agentic setup across Claude Code and Cursor — MCP servers, hooks, skills, agents, rules
---
```

Runs `~/dotfiles/agents/overview.sh`, then interprets the output conversationally. Can answer follow-up questions like "why is X missing from Cursor?" by cross-referencing the shared config.

### 5. `dotfiles doctor --fix`

#### What `--fix` repairs (fast, idempotent, no installs)

1. **Symlinks**: `.zshrc`, `.gitconfig`, `.zprofile`, `.zshenv`, theme, ghostty config
2. **Claude Code config**: runs `agents/claude/setup.sh`
3. **Cursor config**: runs `agents/cursor/setup.sh`
4. **Editor symlinks**: Cursor `settings.json` to `~/Library/Application Support/Cursor/User/`
5. **Obsidian symlinks**: vault config files
6. **Script permissions**: `chmod +x` on scripts

#### What `--fix` skips (left to `install`)

- Homebrew packages and casks
- Runtime installations (Go, Node, Bun, Python, Rust)
- Editor extensions
- Dock layout
- SSH setup
- Git identity prompts
- Oh My Zsh installation

#### Interface

```bash
dotfiles doctor          # Read-only report (unchanged behavior)
dotfiles doctor --fix    # Report + fix config issues
```

#### Implementation

`sub_doctor` gains a `--fix` flag. Each check becomes a function that can optionally apply a fix:

`sub_doctor` gains a `--fix` flag. Each check is a dedicated function (no `eval`), following the existing `check_tool` pattern:

```bash
check_symlink() {
    local name="$1" src="$2" dest="$3"
    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == "$src" ]]; then
        printf "  ${GREEN}✓${NC} %-25s symlinked\n" "$name"
    elif [[ "$FIX" == true ]]; then
        ln -sf "$src" "$dest"
        printf "  ${GREEN}→${NC} %-25s fixed\n" "$name"
    else
        printf "  ${RED}✗${NC} %-25s not symlinked\n" "$name"
        all_ok=false
    fi
}

check_agent_config() {
    local name="$1" setup_script="$2"
    # Check if deployed state matches source (tool-specific logic)
    if [[ "$FIX" == true ]]; then
        . "$setup_script"
        printf "  ${GREEN}→${NC} %-25s redeployed\n" "$name"
    fi
}
```

### 6. Migration Path

All changes are backward-compatible:

1. Move files from `claude/` to `agents/claude/` and from `editors/cursor/` (agent parts) to `agents/cursor/`
2. Update all references in `install.sh`, `bin/dotfiles`, `CLAUDE.md`, `AGENTS.md`
3. Keep `editors/cursor/` for editor settings (`settings.json`, `extensions.sh`, `.cursorignore`)
4. Hook commands in `hooks.json` use `~/dotfiles/` prefix which resolves via shell expansion. The `setup.sh` scripts template `$DOTFILES_DIR` into deployed hook commands to avoid hardcoding. If `~/dotfiles` is not the actual location, `setup.sh` already computes `DOTFILES_DIR` dynamically and uses it for all paths.

### 7. Files Changed/Created

**Moved** (old path → new path):
- `claude/setup.sh` → `agents/claude/setup.sh`
- `claude/global-claude.md` → `agents/claude/global-claude.md`
- `claude/hooks.json` → `agents/claude/hooks.json`
- `claude/hooks/format-on-save.sh` → `agents/claude/hooks/format-on-save.sh`
- `claude/plugins.yaml` → `agents/claude/plugins.yaml`
- `claude/marketplaces.json` → `agents/claude/marketplaces.json`
- `claude/desktop-preferences.json` → `agents/claude/desktop-preferences.json`
- `claude/skills/*` → `agents/claude/skills/*`
- `claude/agents/*` → `agents/claude/agents/*`
- `editors/cursor/cli-config.json` → `agents/cursor/cli-config.json`
- `editors/cursor/skills.sh` → removed (replaced by plugin)
- `editors/cursor/USER_RULES.md` → removed (replaced by auto-deployed rule)

**Created**:
- `agents/shared/mcp-servers.json`
- `agents/shared/rules.md`
- `agents/shared/ignore-patterns`
- `agents/cursor/.cursor-plugin/plugin.json`
- `agents/cursor/setup.sh`
- `agents/cursor/.mcp.json` (generated, gitignored)
- `agents/cursor/rules/shared-rules.mdc` (generated, gitignored)
- `agents/cursor/skills/scaffold-project/SKILL.md`
- `agents/cursor/skills/dotfiles-doctor/SKILL.md`
- `agents/cursor/agents/shellcheck-reviewer.md`
- `agents/cursor/hooks/hooks.json`
- `agents/cursor/hooks/format-on-save-shim.sh`
- `agents/cursor/hooks/guard-destructive.sh`
- `agents/claude/skills/agents-overview/SKILL.md`
- `agents/overview.sh`

**Modified**:
- `install.sh` — update all paths from `claude/` to `agents/claude/`, add `agents/cursor/setup.sh` call
- `bin/dotfiles` — add `agents` subcommand, add `--fix` to `doctor`, update `claude-setup` paths, update completions
- `CLAUDE.md` — update paths
- `AGENTS.md` — update paths
- `README.md` — update directory structure, document new commands

**Remains in `editors/cursor/`**:
- `settings.json`
- `extensions.sh`
- `.cursorignore`
