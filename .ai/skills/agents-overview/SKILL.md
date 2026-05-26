---
name: agents-overview
description: Show the current active agentic setup across Claude Code, Cursor, and Codex — MCP servers, hooks, skills, agents, rules, permissions. Use when user says "show my agent setup", "what's configured", "which MCPs are loaded", "list my skills", "what's the agentic state", "agents-overview"; or wants a snapshot of what tools each AI vendor has access to.
---

# Agents Overview

Show the current state of agentic tool configuration across Claude Code, Cursor, and Codex.

## Workflow

1. Run the overview script:

```bash
~/dotfiles/agents/overview.sh
```

2. Interpret the output for the user
3. If drift is detected (deployed state differs from source config), explain what's out of sync and suggest `dotfiles doctor --fix`
4. Answer follow-up questions by cross-referencing `agents/shared/mcp-servers.json` and each tool's config
