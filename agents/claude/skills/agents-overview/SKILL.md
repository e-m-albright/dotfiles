---
name: agents-overview
description: Show active agentic setup across Claude Code and Cursor — MCP servers, hooks, skills, agents, rules, permissions
---

# Agents Overview

Show the current state of agentic tool configuration across Claude Code and Cursor.

## Workflow

1. Run the overview script:

```bash
~/dotfiles/agents/overview.sh
```

2. Interpret the output for the user
3. If drift is detected (deployed state differs from source config), explain what's out of sync and suggest `dotfiles doctor --fix`
4. Answer follow-up questions by cross-referencing `agents/shared/mcp-servers.json` and each tool's config
