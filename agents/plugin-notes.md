# Plugin & MCP Server Notes

Evaluation notes for plugins, MCP servers, and tools we've tried or considered.
See `claude/plugins.yaml`, `shared/mcp-servers.json`, and `macos/brew.sh` for active configs.

## Removed

| Name | Type | Notes |
|------|------|-------|
| `playwright` | Plugin + MCP | Hasn't worked great. Removed from plugins, MCP servers, and brew. |
| `graphite` / `graphite-mcp` | Plugin (marketplace) + Brew | Not useful enough to justify the plugin/MCP overhead. Removed from plugins, marketplace, and brew. |
| `e2e-testing@hairyf-skills` | Plugin (community) | Playwright-based E2E testing — same issues as the Playwright plugin. |
| `vitest@antfu-skills` | Plugin (community) | Vitest testing — removed community plugins in favor of official marketplace equivalents. |
| `sveltekit-svelte5-tailwind-skill@claude-skills` | Plugin (community) | SvelteKit + Svelte 5 + Tailwind — removed community plugins. |
| `cloudflare@jezweb-claude-skills` | Plugin (community) | Workers, Hono, D1/Drizzle — removed community plugins. |
| `tailwindcss@antfu-skills` | Plugin (community) | Tailwind CSS — removed community plugins. |
| `Notion` | Plugin | Notion is an MCP integration, not a plugin. Removed from plugin list. |

## Disabled

| Name | Type | Notes |
|------|------|-------|
| `cmux` | Brew formula | Nice tool but not helpful over Ghostty. Disabled in `macos/brew.sh`. |

## Considered (not yet enabled)

| Name | Type | Notes |
|------|------|-------|
| `Dagster` | Plugin | Data pipeline orchestration & observability. Listed in `plugins.yaml` as commented-out option. |
