#!/bin/bash
# Cursor agent skills (disabled — prefer MCP servers over skills)
#
# Skills proved less useful than MCP integrations. MCP servers are configured
# in editors/cursor/mcp.json and provide richer tool access.
#
# To re-enable skills: uncomment the SKILLS array and the install loop below.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOTFILES_DIR="${DOTFILES_DIR:-$( cd "$SCRIPT_DIR/../.." && pwd )}"
if [[ -z "${print_section:-}" ]]; then
    source "$DOTFILES_DIR/macos/print_utils.sh"
fi

print_section "Agent skills"
print_info "Skills disabled — using MCP servers instead (see editors/cursor/mcp.json)"

# Disabled skills (kept for reference):
# SKILLS=(
#     # firecrawl — disabled, use Exa AI MCP instead
#     # wshobson/agents/fastapi-templates
#     # wshobson/agents/python-testing-patterns
#     # wshobson/agents/python-performance-optimization
#     # vercel-labs/agent-skills/vercel-react-best-practices
#     # supabase/agent-skills/supabase-postgres-best-practices
#     # anthropics/skills/skill-creator
# )
