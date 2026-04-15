# Cursor 3 Plugin Stack

This file tracks recommended Cursor Marketplace plugins by profile. Install from Cursor chat with `/add-plugin <name>`.

## Ophira Focus (recommended now)

- `superpowers` — guardrails for feature planning/debugging/review loops.
- `context7-plugin` — latest docs for SvelteKit, Rust, and dependency APIs.
- `parallel` (optional) — stronger web research for architecture/library decisions.

## Core (personal + work)

- `superpowers` — process discipline for planning, debugging, and review.
- `context7-plugin` — up-to-date library docs in-agent.

## Personal (default)

- Keep install list lean for daily coding speed.
- Add `cursor-team-kit` only if you want CI/PR automation helpers in personal repos.

## Work profile (install when needed)

- `linear`
- `datadog`
- `slack`
- `cloudflare`
- `notion`

## Consider Later

- `cursor-team-kit` (strong for PR-heavy workflows)
- `posthog`
- `grafana` (not currently found in Cursor Marketplace)
- `clickhouse`
- `langfuse`
- `tldraw`
- `browserstack`

## Revisit / Previously Tried

- `svelte` — removed from default marketplace install checklist and dotfiles-managed MCP defaults; revisit if Svelte-specific editing quality regresses.
- `continual-learning` — removed from recommended install list for now; revisit if long-term workflow memory/learning features become valuable.
- `neon-postgres` — disabled 2026-04-09; revisit when actively using Neon projects.

## Install Notes

- Marketplace plugins can bundle skills, agents, hooks, rules, commands, and MCP servers.
- MCP servers from plugins are toggled under Cursor Settings > Features > Model Context Protocol.
- For Parallel setup, run `/parallel-setup` after install (requires `parallel-cli` auth).
- For profile-specific behavior, use dotfiles-managed MCPs and keep marketplace plugin installs per machine/account.

## Install Commands

- `/add-plugin superpowers`
- `/add-plugin context7-plugin`
- `/add-plugin parallel` (optional)
- `/add-plugin cursor-team-kit` (optional)
- `/add-plugin tldraw` (optional)
