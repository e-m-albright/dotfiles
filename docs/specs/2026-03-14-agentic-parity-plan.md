# Agentic Parity Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify Claude Code and Cursor agentic config under `agents/` with shared MCP servers, rules, and ignore patterns; add `dotfiles agents` overview command and `dotfiles doctor --fix`.

**Architecture:** Move agentic config from `claude/` and `editors/cursor/` into `agents/{shared,claude,cursor}`. Each tool has a `setup.sh` that reads shared config and deploys tool-specific formats. `agents/cursor/` is itself a Cursor plugin. `agents/overview.sh` powers the `dotfiles agents` CLI command and a Claude Code skill.

**Tech Stack:** Bash, jq, yq (existing dotfiles tooling)

**Spec:** `docs/specs/2026-03-14-agentic-parity-design.md`

---

## Chunk 1: Directory Restructure + Shared Config

### Task 1: Create shared config layer

**Files:**
- Create: `agents/shared/mcp-servers.json`
- Create: `agents/shared/rules.md`
- Create: `agents/shared/ignore-patterns`

- [ ] **Step 1: Create `agents/shared/mcp-servers.json`**

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

- [ ] **Step 2: Create `agents/shared/rules.md`**

Merge content from `claude/global-claude.md` and `editors/cursor/USER_RULES.md`, deduplicated. Keep only the shared guardrails — tool-specific sections (Claude's command style, Cursor's Drata/Rootly mentions) stay in their respective tool configs. See spec section 2 for exact content.

- [ ] **Step 3: Create `agents/shared/ignore-patterns`**

Plain text, one pattern per line. Extract common patterns from `editors/cursor/.cursorignore`:

```
node_modules/
.next/
out/
dist/
build/
coverage/
.nyc_output/
.env
.env.*
*.log
*.min.js
*.min.css
*.bundle.js
__pycache__/
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 4: Validate JSON**

Run: `jq '.' agents/shared/mcp-servers.json`
Expected: valid JSON output

- [ ] **Step 5: Commit**

```bash
git add agents/shared/
git commit -m "feat: add agents/shared/ config layer (MCP servers, rules, ignore patterns)"
```

---

### Task 2: Move Claude Code config to `agents/claude/`

**Files:**
- Move: `claude/*` → `agents/claude/*`
- Delete: `claude/mcp.json` (replaced by shared source)

- [ ] **Step 1: Move all files from `claude/` to `agents/claude/`**

```bash
mkdir -p agents/claude/hooks agents/claude/skills agents/claude/agents
git mv claude/setup.sh agents/claude/setup.sh
git mv claude/global-claude.md agents/claude/global-claude.md
git mv claude/hooks.json agents/claude/hooks.json
git mv claude/hooks/format-on-save.sh agents/claude/hooks/format-on-save.sh
git mv claude/plugins.yaml agents/claude/plugins.yaml
git mv claude/marketplaces.json agents/claude/marketplaces.json
git mv claude/desktop-preferences.json agents/claude/desktop-preferences.json
git mv claude/skills/scaffold-project agents/claude/skills/scaffold-project
git mv claude/skills/dotfiles-doctor agents/claude/skills/dotfiles-doctor
git mv claude/agents/shellcheck-reviewer.md agents/claude/agents/shellcheck-reviewer.md
```

- [ ] **Step 2: Remove `claude/mcp.json`** (will be generated from shared source)

```bash
git rm claude/mcp.json
```

- [ ] **Step 3: Remove empty `claude/` directory**

```bash
rmdir claude/agents claude/skills claude/hooks claude 2>/dev/null || true
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move claude/ to agents/claude/"
```

---

### Task 3: Move Cursor agent config to `agents/cursor/`

**Files:**
- Move: `editors/cursor/cli-config.json` → `agents/cursor/cli-config.json`
- Delete: `editors/cursor/skills.sh` (replaced by plugin)
- Delete: `editors/cursor/USER_RULES.md` (replaced by auto-deployed rule)
- Keep: `editors/cursor/settings.json`, `editors/cursor/extensions.sh`, `editors/cursor/.cursorignore`

- [ ] **Step 1: Move agentic files**

```bash
mkdir -p agents/cursor
git mv editors/cursor/cli-config.json agents/cursor/cli-config.json
```

- [ ] **Step 2: Remove replaced files**

```bash
git rm editors/cursor/skills.sh
git rm editors/cursor/USER_RULES.md
git rm editors/cursor/mcp.json
```

`mcp.json` is replaced by the generated `agents/cursor/.mcp.json` from the shared source.

- [ ] **Step 3: Verify `editors/cursor/` still has editor files**

```bash
ls editors/cursor/
```

Expected: `settings.json`, `extensions.sh`, `.cursorignore`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: split editors/cursor/ — agentic config to agents/cursor/, editor settings stay"
```

---

### Task 4: Update all path references

**Files:**
- Modify: `install.sh`
- Modify: `bin/dotfiles`
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update `install.sh` — Claude Code paths only**

Replace `$DOTFILES_DIR/claude/` references with `$DOTFILES_DIR/agents/claude/`. Only handle Claude Code path changes here — Cursor-specific install.sh changes are in Task 15.

- Line ~274: `. "$DOTFILES_DIR/claude/setup.sh"` → `. "$DOTFILES_DIR/agents/claude/setup.sh"`
- Line ~301: `~/dotfiles/claude/plugins.yaml` → `~/dotfiles/agents/claude/plugins.yaml`

- [ ] **Step 2: Update `bin/dotfiles`**

Change `sub_claude_setup` to source from `agents/claude/setup.sh`:

```bash
sub_claude_setup() {
    . "$DOTFILES_DIR/agents/claude/setup.sh"
    printf "${GREEN}%b Claude Code setup complete.${NC}\n" "$ARROW"
}
```

- [ ] **Step 3: Update `CLAUDE.md`**

Replace `claude/` path references with `agents/claude/`. Update directory description.

- [ ] **Step 4: Update `AGENTS.md`**

Replace `claude/` reference with `agents/claude/` in the "What This Repo Contains" section.

- [ ] **Step 5: Update `.gitignore`**

Add entries for generated files in `agents/cursor/`:

```
# Generated by agents/cursor/setup.sh from agents/shared/
agents/cursor/.mcp.json
agents/cursor/rules/shared-rules.mdc
```

- [ ] **Step 6: Verify nothing references old `claude/` paths**

```bash
grep -r 'claude/setup\|claude/hooks\|claude/plugins\|claude/mcp\|claude/global-claude\|claude/marketplaces\|claude/desktop' --include='*.sh' --include='*.md' --include='*.json' .
```

Expected: only matches in `agents/claude/` or docs, not bare `claude/`

- [ ] **Step 7: Commit**

```bash
git add install.sh bin/dotfiles CLAUDE.md AGENTS.md .gitignore
git commit -m "refactor: update all path references from claude/ to agents/claude/"
```

---

## Chunk 2: Claude Code Setup Refactor

### Task 5: Refactor `agents/claude/setup.sh` to use shared MCP source

**Files:**
- Modify: `agents/claude/setup.sh`

- [ ] **Step 1: Replace `setup_mcp` function**

Replace the function that reads from a local `mcp.json` with one that reads from `agents/shared/mcp-servers.json` and filters for `targets` containing `"claude"`:

```bash
setup_mcp() {
    local shared_mcp="$DOTFILES_DIR/agents/shared/mcp-servers.json"
    [[ -f "$shared_mcp" ]] || { print_info "No shared mcp-servers.json — skipping MCP setup"; return 0; }
    require_jq || return 0

    mkdir -p "$HOME/.claude"
    [[ -f "$CLAUDE_JSON" ]] || echo '{}' > "$CLAUDE_JSON"
    cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"

    # Filter servers targeting "claude", strip targets field
    local mcp_servers
    mcp_servers=$(jq '
        to_entries
        | map(select(.value.targets | index("claude")))
        | map({key: .key, value: (.value | del(.targets))})
        | from_entries
    ' "$shared_mcp")

    jq --argjson servers "$mcp_servers" '.mcpServers = ($servers + (.mcpServers // {}))' "$CLAUDE_JSON.bak" > "$CLAUDE_JSON"

    local count
    count=$(echo "$mcp_servers" | jq 'length')
    print_success "Configured $count MCP servers (Claude Code)"
}
```

- [ ] **Step 2: Update `setup_desktop` similarly**

Same jq filter but writes to `$DESKTOP_CONFIG` instead of `$CLAUDE_JSON`.

- [ ] **Step 3: Update path variables at top of file**

```bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
```

Remove `MCP_JSON` variable (no longer used). Update `HOOKS_JSON`, `PLUGINS_YAML`, `GLOBAL_CLAUDE_MD`, `DESKTOP_PREFS`, `MARKETPLACES_JSON` to use `$SCRIPT_DIR`.

- [ ] **Step 4: Update `hooks.json` hook command paths**

In `agents/claude/hooks.json`, update the format-on-save command path:

```json
"command": "~/dotfiles/agents/claude/hooks/format-on-save.sh"
```

Actually — `setup.sh` should template `$DOTFILES_DIR` into hook commands when deploying. Add a `setup_hooks` step that does `sed` replacement of `$DOTFILES_DIR` in the hooks before writing to settings.

- [ ] **Step 5: Test setup script**

```bash
bash -n agents/claude/setup.sh
```

Expected: no syntax errors

- [ ] **Step 6: Commit**

```bash
git add agents/claude/setup.sh agents/claude/hooks.json
git commit -m "refactor: agents/claude/setup.sh reads shared MCP source"
```

---

### Task 6: Update `global-claude.md` to reference shared rules

**Files:**
- Modify: `agents/claude/global-claude.md`

- [ ] **Step 1: Restructure `global-claude.md`**

This is a one-time manual edit (not generated at deploy time — `setup.sh` copies the file as-is to `~/.claude/CLAUDE.md`).

Replace the current content with:
1. First line: `Read and follow the instructions in AGENTS.md in this repository if present. Look for ABSTRACT.md for context on this repository.`
2. Second line: `Read all .ai/rules/*.mdc files for process and coding conventions.`
3. Then the full content of `agents/shared/rules.md` (copy-paste, not import)
4. Then the Claude-specific sections that aren't shared:
   - "Command style" section (prefer dedicated tools, single commands, heredocs)
   - "Worktrees for isolation" bullet

Remove any content already covered by `agents/shared/rules.md` to avoid duplication.

- [ ] **Step 2: Commit**

```bash
git add agents/claude/global-claude.md
git commit -m "feat: global-claude.md incorporates shared rules"
```

---

### Task 7: Create `agents-overview` Claude Code skill

**Files:**
- Create: `agents/claude/skills/agents-overview/SKILL.md`

- [ ] **Step 1: Create skill file**

```markdown
---
name: agents-overview
description: Show active agentic setup across Claude Code and Cursor — MCP servers, hooks, skills, agents, rules, permissions
---

# Agents Overview

Show the current state of agentic tool configuration across Claude Code and Cursor.

## Workflow

1. Run the overview script:

\`\`\`bash
~/dotfiles/agents/overview.sh
\`\`\`

2. Interpret the output for the user
3. If drift is detected (deployed state differs from source config), explain what's out of sync and suggest `dotfiles doctor --fix`
4. Answer follow-up questions by cross-referencing `agents/shared/mcp-servers.json` and each tool's config
```

- [ ] **Step 2: Commit**

```bash
git add agents/claude/skills/agents-overview/
git commit -m "feat: add agents-overview Claude Code skill"
```

---

## Chunk 3: Cursor Plugin

### Task 8: Create Cursor plugin structure

**Files:**
- Create: `agents/cursor/.cursor-plugin/plugin.json`
- Create: `agents/cursor/skills/scaffold-project/SKILL.md`
- Create: `agents/cursor/skills/dotfiles-doctor/SKILL.md`
- Create: `agents/cursor/agents/shellcheck-reviewer.md`

- [ ] **Step 1: Create plugin manifest**

```bash
mkdir -p agents/cursor/.cursor-plugin
```

Write `agents/cursor/.cursor-plugin/plugin.json`:

```json
{
  "name": "dotfiles",
  "description": "Personal agentic config — rules, skills, agents, hooks",
  "version": "1.0.0",
  "author": { "name": "evan" }
}
```

- [ ] **Step 2: Create skills**

Create `agents/cursor/skills/scaffold-project/SKILL.md` and `agents/cursor/skills/dotfiles-doctor/SKILL.md`. Use the same content as the Claude Code versions — the SKILL.md format is cross-compatible (both tools use the agentskills.io spec).

These are **independent copies**, not symlinks. This is intentional: if a tool requires adaptation later (e.g., Cursor-specific tool names), the copy can diverge. For now they're identical.

- [ ] **Step 3: Create agent**

Copy `agents/claude/agents/shellcheck-reviewer.md` to `agents/cursor/agents/shellcheck-reviewer.md`. Same content — uses portable `find` + `shellcheck`.

- [ ] **Step 4: Commit**

```bash
git add agents/cursor/.cursor-plugin agents/cursor/skills agents/cursor/agents
git commit -m "feat: create Cursor plugin structure (skills, agents)"
```

---

### Task 9: Create Cursor hooks

**Files:**
- Create: `agents/cursor/hooks/hooks.json`
- Create: `agents/cursor/hooks/format-on-save-shim.sh`
- Create: `agents/cursor/hooks/guard-destructive.sh`

- [ ] **Step 1: Create `hooks/hooks.json`**

```json
{
  "hooks": [
    {
      "event": "afterFileEdit",
      "command": "~/dotfiles/agents/cursor/hooks/format-on-save-shim.sh",
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

- [ ] **Step 2: Create `hooks/format-on-save-shim.sh`**

Normalizes Cursor's hook stdin to the format `format-on-save.sh` expects, then delegates:

```bash
#!/usr/bin/env bash
# Shim: normalize Cursor afterFileEdit input to Claude Code PostToolUse format.
# Cursor may provide file path under different JSON keys.
# This shim tries multiple keys and forwards to the shared formatter.

set -eo pipefail

INPUT=$(cat)

# Try Cursor's likely key names, fall back to Claude Code's format
FILE=$(echo "$INPUT" | jq -r '.filePath // .file_path // .tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

# Forward in Claude Code's expected format
echo "{\"tool_input\": {\"file_path\": \"$FILE\"}}" | \
    "$(dirname "$0")/../../claude/hooks/format-on-save.sh"
```

- [ ] **Step 3: Create `hooks/guard-destructive.sh`**

```bash
#!/usr/bin/env bash
# Guard against destructive shell commands in Cursor agent.
# Exit 2 to block the command.

set -eo pipefail

CMD=$(jq -r '.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0

case "$CMD" in
    *"rm -rf /"*|*"rm -rf ~"*|*"rm -rf \$HOME"*)
        echo "BLOCK: Destructive rm command" >&2
        exit 2 ;;
    *"git reset --hard"*|*"git clean -fd"*|*"git checkout -- ."*)
        echo "BLOCK: Destructive git command — confirm manually" >&2
        exit 2 ;;
    *"sudo rm"*|*"sudo dd"*)
        echo "BLOCK: Privileged destructive command" >&2
        exit 2 ;;
esac
```

- [ ] **Step 4: Make scripts executable**

```bash
chmod +x agents/cursor/hooks/format-on-save-shim.sh agents/cursor/hooks/guard-destructive.sh
```

- [ ] **Step 5: Commit**

```bash
git add agents/cursor/hooks/
git commit -m "feat: add Cursor hooks (format-on-save shim, destructive command guard)"
```

---

### Task 10: Update `cli-config.json` with modern permissions

**Files:**
- Modify: `agents/cursor/cli-config.json`

- [ ] **Step 1: Rewrite with modern permission syntax**

See spec section 3 for exact content. Key changes:
- Replace `read.files`, `search.codebase`, etc. with `Shell(git)`, `Read(**)`, `Write(src/**)` format
- Add deny rules for sensitive files
- Add attribution config

- [ ] **Step 2: Validate JSON**

```bash
jq '.' agents/cursor/cli-config.json
```

- [ ] **Step 3: Commit**

```bash
git add agents/cursor/cli-config.json
git commit -m "feat: update Cursor CLI permissions to modern format"
```

---

### Task 11: Create `agents/cursor/setup.sh`

**Files:**
- Create: `agents/cursor/setup.sh`

- [ ] **Step 1: Write setup script**

```bash
#!/usr/bin/env bash
# Deploy Cursor agentic config: MCP servers, rules, cli-config, plugin registration.
# Idempotent — safe to run multiple times.

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SHARED_DIR="$DOTFILES_DIR/agents/shared"

# Source print utils
source "$DOTFILES_DIR/macos/print_utils.sh" 2>/dev/null || true

require_jq() {
    command -v jq >/dev/null 2>&1 || { print_warning "jq not found — skipping"; return 1; }
}

# --- Generate .mcp.json from shared source ---
setup_mcp() {
    [[ -f "$SHARED_DIR/mcp-servers.json" ]] || return 0
    require_jq || return 0

    jq '{mcpServers: (
        to_entries
        | map(select(.value.targets | index("cursor")))
        | map({key: .key, value: (.value | del(.targets))})
        | from_entries
    )}' "$SHARED_DIR/mcp-servers.json" > "$SCRIPT_DIR/.mcp.json"

    local count
    count=$(jq '.mcpServers | length' "$SCRIPT_DIR/.mcp.json")
    print_success "Generated .mcp.json ($count servers)"
}

# --- Generate rules from shared source ---
setup_rules() {
    [[ -f "$SHARED_DIR/rules.md" ]] || return 0
    mkdir -p "$SCRIPT_DIR/rules"

    cat > "$SCRIPT_DIR/rules/shared-rules.mdc" << RULES_EOF
---
description: Shared agentic guardrails — process, safety, context, testing
alwaysApply: true
---

$(cat "$SHARED_DIR/rules.md")
RULES_EOF

    print_success "Generated rules/shared-rules.mdc"
}

# --- Deploy cli-config.json ---
setup_cli_config() {
    mkdir -p ~/.cursor
    if [[ -f "$SCRIPT_DIR/cli-config.json" ]]; then
        ln -sf "$SCRIPT_DIR/cli-config.json" ~/.cursor/cli-config.json
        print_success "Deployed cli-config.json"
    fi
}

# --- Register as local plugin ---
# NOTE: The spec suggests writing to ~/.cursor/extensions/extensions.json with @local suffix.
# This plan uses a simpler symlink approach to ~/.cursor/plugins/ which is another
# documented discovery path. During implementation, verify which mechanism works by
# checking if Cursor loads the plugin. If symlink doesn't work, fall back to the
# extensions.json registry approach.
setup_plugin() {
    mkdir -p ~/.cursor/plugins
    if [[ -L ~/.cursor/plugins/dotfiles ]] && [[ "$(readlink ~/.cursor/plugins/dotfiles)" == "$SCRIPT_DIR" ]]; then
        print_skip "Plugin already registered"
    else
        ln -sf "$SCRIPT_DIR" ~/.cursor/plugins/dotfiles
        print_success "Registered dotfiles plugin (~/.cursor/plugins/dotfiles)"
    fi
    print_info "Ensure third-party plugins are enabled: Cursor Settings > Features"
}

# --- Generate .cursorignore from shared patterns ---
setup_cursorignore() {
    [[ -f "$SHARED_DIR/ignore-patterns" ]] || return 0
    local cursor_ignore="$DOTFILES_DIR/editors/cursor/.cursorignore"

    cat > "$cursor_ignore" << 'HEADER'
# Cursor ignore file
# AUTO-GENERATED from agents/shared/ignore-patterns + Cursor-specific additions
# Do not edit directly — modify agents/shared/ignore-patterns instead

HEADER

    cat "$SHARED_DIR/ignore-patterns" >> "$cursor_ignore"

    cat >> "$cursor_ignore" << 'CURSOR_SPECIFIC'

# Cursor-specific
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db
.cache/
CURSOR_SPECIFIC

    print_success "Generated .cursorignore"
}

# --- Main ---
setup_mcp
setup_rules
setup_cli_config
setup_plugin
setup_cursorignore
```

- [ ] **Step 2: Make executable**

```bash
chmod +x agents/cursor/setup.sh
```

- [ ] **Step 3: Test syntax**

```bash
bash -n agents/cursor/setup.sh
```

- [ ] **Step 4: Commit**

```bash
git add agents/cursor/setup.sh
git commit -m "feat: add agents/cursor/setup.sh — deploys Cursor agentic config"
```

---

## Chunk 4: Overview Command + Doctor Fix

### Task 12: Create `agents/overview.sh`

**Files:**
- Create: `agents/overview.sh`

- [ ] **Step 1: Write the overview script**

Structure:

```bash
#!/usr/bin/env bash
# Agentic setup overview — reports what's active across Claude Code and Cursor.
# Called by: dotfiles agents

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
source "$DOTFILES_DIR/macos/print_utils.sh"

# Deployed config locations
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"
CURSOR_PLUGIN="$HOME/.cursor/plugins/dotfiles"

# Source config locations
SHARED_MCP="$SCRIPT_DIR/shared/mcp-servers.json"
CLAUDE_HOOKS="$SCRIPT_DIR/claude/hooks.json"
CURSOR_HOOKS="$SCRIPT_DIR/cursor/hooks/hooks.json"

has_jq() { command -v jq >/dev/null 2>&1; }

# --- Section: MCP Servers ---
section_mcp() {
    print_section "MCP Servers"
    # Read shared source, for each server print name + which tools target it
    # Then check deployed state: ~/.claude.json and cursor plugin .mcp.json
    # Flag if deployed differs from source
    has_jq || { print_warning "jq required"; return; }
    printf "  %-15s %-12s %-12s %s\n" "Server" "Claude" "Cursor" "Source"
    printf "  %-15s %-12s %-12s %s\n" "───────" "──────" "──────" "──────"
    jq -r 'to_entries[] | "\(.key) \(.value.targets | join(","))"' "$SHARED_MCP" | \
    while read -r name targets; do
        local claude_mark="—" cursor_mark="—"
        [[ "$targets" == *claude* ]] && claude_mark="✓"
        [[ "$targets" == *cursor* ]] && cursor_mark="✓"
        printf "  %-15s %-12s %-12s %s\n" "$name" "$claude_mark" "$cursor_mark" "shared"
    done
}

# --- Section: Hooks ---
section_hooks() { ... }  # Similar pattern — read source JSON, list events

# --- Section: Skills ---
section_skills() {
    print_section "Skills"
    printf "  %-20s %-12s %-12s %s\n" "Skill" "Claude" "Cursor" "Invocation"
    printf "  %-20s %-12s %-12s %s\n" "───────" "──────" "──────" "──────────"
    # List claude skills
    for skill_dir in "$SCRIPT_DIR"/claude/skills/*/; do
        [[ -d "$skill_dir" ]] || continue
        local name=$(basename "$skill_dir")
        local claude_mark="✓" cursor_mark="—"
        [[ -d "$SCRIPT_DIR/cursor/skills/$name" ]] && cursor_mark="✓"
        # Check invocation mode from SKILL.md frontmatter
        local invocation="both"
        grep -q 'disable-model-invocation: true' "$skill_dir/SKILL.md" 2>/dev/null && invocation="user-only"
        grep -q 'user-invocable: false' "$skill_dir/SKILL.md" 2>/dev/null && invocation="model-only"
        printf "  %-20s %-12s %-12s %s\n" "$name" "$claude_mark" "$cursor_mark" "$invocation"
    done
}

# --- Section: Agents ---
section_agents() { ... }  # Same pattern — list .md files in agents/ dirs

# --- Section: Rules ---
section_rules() { ... }  # Show shared/rules.md → where deployed for each tool

# --- Section: Permissions ---
section_permissions() {
    print_section "Permissions"
    # Count Claude Code permission rules
    if has_jq && [[ -f "$CLAUDE_SETTINGS" ]]; then
        local cc_count=$(jq '[.permissions.allow // [] | length, .permissions.deny // [] | length] | add' "$CLAUDE_SETTINGS" 2>/dev/null || echo 0)
        printf "  Claude Code: %s rules\n" "$cc_count"
    fi
    # Count Cursor permission rules
    if has_jq && [[ -f "$SCRIPT_DIR/cursor/cli-config.json" ]]; then
        local cur_count=$(jq '[.permissions.allow // [] | length, .permissions.deny // [] | length] | add' "$SCRIPT_DIR/cursor/cli-config.json" 2>/dev/null || echo 0)
        printf "  Cursor CLI:  %s rules\n" "$cur_count"
    fi
}

# --- Main ---
print_header "Agentic Setup Overview"
section_mcp
section_hooks
section_skills
section_agents
section_rules
section_permissions
```

Fill in the `{ ... }` sections following the same read-source-then-check-deployed pattern. Each section is self-contained. Gracefully skip sections if jq is missing or a tool isn't installed.

- [ ] **Step 2: Make executable**

```bash
chmod +x agents/overview.sh
```

- [ ] **Step 3: Test syntax**

```bash
bash -n agents/overview.sh
```

- [ ] **Step 4: Commit**

```bash
git add agents/overview.sh
git commit -m "feat: add agents/overview.sh — agentic setup report engine"
```

---

### Task 13: Add `dotfiles agents` subcommand

**Files:**
- Modify: `bin/dotfiles`

- [ ] **Step 1: Add `sub_agents` function**

After the existing `sub_stale` function:

```bash
sub_agents() {
    "$DOTFILES_DIR/agents/overview.sh" "$@"
}
```

- [ ] **Step 2: Add to help text**

In `sub_help`, add:

```bash
printf "   agents           Show active agentic setup (Claude Code + Cursor)\n"
```

- [ ] **Step 3: Add to case statement**

The existing `case $COMMAND_NAME` catches known commands. Add `agents)` case:

```bash
    agents)
        sub_agents
        ;;
```

- [ ] **Step 4: Add to completions**

In `sub_completions`, add to the `commands` array:

```bash
'agents:Show active agentic setup'
```

- [ ] **Step 5: Commit**

```bash
git add bin/dotfiles
git commit -m "feat: add 'dotfiles agents' subcommand"
```

---

### Task 14: Add `dotfiles doctor --fix`

**Files:**
- Modify: `bin/dotfiles`

- [ ] **Step 1: Add `--fix` flag parsing to `sub_doctor`**

At the start of `sub_doctor`, add:

```bash
local FIX=false
if [[ "${1:-}" == "--fix" ]]; then
    FIX=true
    shift
fi
```

- [ ] **Step 2: Add `check_symlink` helper**

```bash
check_symlink() {
    local name="$1" src="$2" dest="$3"
    if [[ -L "$dest" ]] && [[ "$(readlink "$dest")" == *"$src"* ]]; then
        printf "  ${GREEN}✓${NC} %-25s symlinked\n" "$name"
    elif [[ "$FIX" == true ]]; then
        ln -sf "$src" "$dest"
        printf "  ${GREEN}→${NC} %-25s fixed\n" "$name"
    else
        printf "  ${RED}✗${NC} %-25s not symlinked\n" "$name"
        all_ok=false
    fi
}
```

- [ ] **Step 3: Add Configuration checks with fix capability**

After the existing Configuration section in `sub_doctor`, add fixable checks:

```bash
# Symlink checks (fixable)
check_symlink ".zshrc" "$DOTFILES_DIR/shell/.zshrc" ~/.zshrc
check_symlink ".gitconfig" "$DOTFILES_DIR/git/.gitconfig" ~/.gitconfig
check_symlink ".zprofile" "$DOTFILES_DIR/shell/.zprofile" ~/.zprofile

# Agent config checks (fixable)
if [[ "$FIX" == true ]]; then
    printf "\n${BLUE}Redeploying agent configs...${NC}\n"
    if [[ -f "$DOTFILES_DIR/agents/claude/setup.sh" ]]; then
        . "$DOTFILES_DIR/agents/claude/setup.sh"
    fi
    if [[ -f "$DOTFILES_DIR/agents/cursor/setup.sh" ]]; then
        . "$DOTFILES_DIR/agents/cursor/setup.sh"
    fi
fi
```

- [ ] **Step 4: Update help text**

Change doctor help line:

```bash
printf "   doctor           Check all tools are installed (--fix to repair config)\n"
```

- [ ] **Step 5: Update completions**

```bash
'doctor:Check that all tools are installed (--fix to repair)'
```

- [ ] **Step 6: Pass args through in case statement**

The `doctor` case in the main case statement needs to pass args:

```bash
    doctor)
        shift
        sub_doctor "$@"
        ;;
```

- [ ] **Step 7: Commit**

```bash
git add bin/dotfiles
git commit -m "feat: add 'dotfiles doctor --fix' for lightweight config repair"
```

---

## Chunk 5: Update install.sh + README + Final Integration

### Task 15: Update `install.sh` — Cursor section

**Files:**
- Modify: `install.sh`

Note: Claude Code paths were already updated in Task 4. This task handles Cursor-specific changes only.

- [ ] **Step 1: Update Cursor section**

Replace the skills.sh sourcing line with cursor setup.sh:
```bash
. "$DOTFILES_DIR/agents/cursor/setup.sh"
```

Remove the old `cursor/mcp.json` symlink line (setup.sh generates and registers the plugin now):
```bash
# Remove this line:
ln -sf "$DOTFILES_DIR/editors/cursor/mcp.json" ~/.cursor/mcp.json 2>/dev/null || true
```

Also remove the `cli-config.json` symlink line (cursor setup.sh handles this now):
```bash
# Remove this line:
ln -sf "$DOTFILES_DIR/editors/cursor/cli-config.json" ~/.cursor/cli-config.json 2>/dev/null || true
```

Keep the `settings.json` symlink — that's an editor setting, not agentic.

- [ ] **Step 2: Verify `.agents/` path is unchanged**

```bash
"$DOTFILES_DIR/.agents/generate-permissions.sh" claude || true
```

This path stays the same (`.agents/` is the project scaffolding working dir, not the new `agents/` dir).

- [ ] **Step 4: Test syntax**

```bash
bash -n install.sh
```

- [ ] **Step 5: Commit**

```bash
git add install.sh
git commit -m "refactor: install.sh uses agents/ paths, adds Cursor setup.sh"
```

---

### Task 16: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update directory structure diagram**

Replace the old structure with one showing `agents/` and the slimmed `editors/`.

- [ ] **Step 2: Update Claude Code section**

Document skills, agents, shared MCP source.

- [ ] **Step 3: Update External Connections table**

- GitHub: add MCP alongside CLI
- Add Notion to Cursor column
- Add Context7 to the table properly

- [ ] **Step 4: Add `dotfiles agents` to command list**

```bash
dotfiles agents             # Show active agentic setup (Claude Code + Cursor)
```

- [ ] **Step 5: Update `dotfiles doctor` line**

```bash
dotfiles doctor              # Check all tools are installed (--fix to repair config)
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: update README for agents/ restructure, new commands"
```

---

### Task 17: Final verification

- [ ] **Step 1: Verify no broken references**

```bash
grep -rn 'claude/setup\|claude/hooks\|claude/plugins\|claude/mcp\.json\|editors/cursor/cli-config\|editors/cursor/skills\|editors/cursor/USER_RULES' \
  --include='*.sh' --include='*.md' --include='*.json' . | \
  grep -v 'agents/claude\|docs/specs\|node_modules'
```

Expected: no matches (all old paths updated)

- [ ] **Step 2: Validate all JSON files**

```bash
for f in agents/shared/mcp-servers.json agents/cursor/.cursor-plugin/plugin.json agents/cursor/cli-config.json agents/claude/hooks.json; do
    jq '.' "$f" >/dev/null && echo "OK: $f" || echo "FAIL: $f"
done
```

- [ ] **Step 3: Check all scripts parse**

```bash
for f in agents/claude/setup.sh agents/cursor/setup.sh agents/overview.sh agents/claude/hooks/format-on-save.sh agents/cursor/hooks/format-on-save-shim.sh agents/cursor/hooks/guard-destructive.sh; do
    bash -n "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

- [ ] **Step 4: Run `dotfiles doctor`**

```bash
bin/dotfiles doctor
```

Verify it runs without errors.

- [ ] **Step 5: Run `dotfiles agents`**

```bash
bin/dotfiles agents
```

Verify it produces the overview report.

- [ ] **Step 6: Final commit if any fixups needed**

```bash
git add -A
git status
# Only commit if there are changes
git diff --cached --quiet || git commit -m "fix: address integration issues from agentic parity migration"
```
