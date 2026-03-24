# Plugin & MCP Server Notes

Evaluation notes for plugins, MCP servers, and tools we've tried or considered.
See `claude/plugins.yaml`, `shared/mcp-servers.json`, and `macos/brew.sh` for active configs.

## Disabled

| Name | Type | Notes |
|------|------|-------|
| `playwright` | Plugin + MCP | Hasn't worked great so far. Removed from `shared/mcp-servers.json` and `editors/cursor/mcp.json`. |
| `graphite` / `graphite-mcp` | Plugin (marketplace) | Needs more investigation on how to properly use it. Marketplace entry removed from `claude/marketplaces.json`. |
| `e2e-testing@hairyf-skills` | Plugin (community) | Playwright-based E2E testing — same issues as the Playwright plugin above. |
| `cmux` | Brew formula | Nice tool but not helpful over Ghostty. Disabled in `macos/brew.sh`. |

## Considered (not yet enabled)

| Name | Type | Notes |
|------|------|-------|
| `Dagster` | Plugin | Data pipeline orchestration & observability. Listed in `plugins.yaml` as commented-out option. |
