---
name: browser-tooling
description: Pick the right browser/UI tool for the job — routes between Playwright tests (deterministic), the agent-browser CLI (default for agent-driven browsing), and pinchtab (human-in-the-loop authed sessions). Use when user reports a UI bug, asks to verify a deployed page, wants E2E coverage, says "look at this page", "did the deploy work", "check the UI", "automate the browser", or "drive Chrome".
---

# Browser Tooling Router

These tools sit at **different layers of the stack**, not in competition:

```
AI Agent  →  control layer (agent-browser / pinchtab)  →  CDP  →  Chrome
              automation framework (Playwright)  ──────────┘
```

- **Playwright** — automation *framework*. You (or a test) write code that says exactly what to do. Most reliable; the testing/scraping/production foundation. Not agent-native (the LLM must emit Playwright code).
- **agent-browser** (Vercel Labs) — agent-native browser *CLI*. Compact text/a11y representations, `agent-browser open … / click @e2 / fill @e3 "…"`. Token-efficient, fast, shells out — **no MCP context tax.**
- **pinchtab** — agent-oriented control *server*: a persistent, logged-in, watchable browser over a lightweight HTTP API + accessibility snapshots. Best when a human watches/intervenes on an authed site.

**The stack we run (your endorsement): Playwright + agent-browser for ~90% of work; pinchtab on standby for human-in-the-loop authed sessions.** Chrome DevTools is **not** an explicitly-supported standing tool, and there are **no browser MCP servers loaded** — the CLI layer gives the same agent-native control (a11y snapshots, persistent session) without paying a per-session context tax.

## Decision tree

**"Look at this page" / "Did the deploy work?" / smoke check / drive a flow** → **agent-browser CLI** (default)
- `agent-browser open <url>`, then `click @e2` / `fill @e3 "…"` / snapshot. ~200–400 tokens/page.
- First choice for almost everything an agent does in a browser.

**Human-in-the-loop on a logged-in site (you watch, agent drives)** → **pinchtab** (standby)
- `pinchtab serve --port 9867` then `curl localhost:9867/snapshot`. ~800 tokens/page.
- Reach for it only when agent-browser's headless model isn't enough — i.e. you need a persistent, visible, authenticated browser.

**"Catch this regression forever" / deterministic scrape / production workflow** → **Playwright tests**
- Free per run. Write tests in the project's `web/tests/e2e/`. Use Daily fake-media flags for WebRTC.
- After root-causing a bug with the CLI, write a Playwright test so it can never silently regress.

**"Long agentic flow across 20 screens where selectors rot"** → **Stagehand** (per-project)
- `@browserbasehq/stagehand` — natural-language `act`/`extract`/`observe`. Costs LLM tokens per run. Install per-project, not global.

**"Why is this slow / what error fired / network looks wrong"** → no standing tool
- We dropped the Chrome DevTools MCP (overlap + context tax). If you genuinely need perf/network/console traces, launch `npx chrome-devtools-mcp@latest` ad-hoc for that one session, then drop it — don't make it standing.

## Token budget reference

| Tool | Layer | Cost shape |
|------|-------|------------|
| Playwright tests in CI | framework | 0 / run (one-time write cost) |
| agent-browser CLI | agent control | ~200–400 tokens / page · no MCP tax |
| pinchtab CLI/server | agent control | ~800 tokens / page · no MCP tax |
| Stagehand | agent framework | LLM tokens / test run |
| ~~Playwright MCP~~ | dropped | was ~13.7k always-on context |
| ~~Chrome DevTools MCP~~ | dropped | was ~18k always-on context · launch ad-hoc if ever needed |

## Why CLI, not MCP, for browser control

An MCP server taxes every session's context with its tool schemas whether or not you browse. The agent-native value of Playwright-MCP / pinchtab-MCP — **structured a11y snapshots + a persistent browser session** — is exactly what `agent-browser` (CLI) and `pinchtab` (server) already give you on demand, at zero standing cost. Note Playwright-the-framework (tests) is a *different layer* from Playwright-MCP (agent control); we keep the former, drop the latter. So nothing is lost by removing the browser MCPs.

## Workflow patterns

**Bug report → permanent test:**
1. Reproduce/poke with `agent-browser` (or pinchtab if you need to watch a logged-in session).
2. Once root-caused, write a Playwright test so it's protected forever.

**WebRTC / Daily.co:** Playwright tests — `--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream`, `--use-file-for-fake-audio-capture=path.wav`, `--use-file-for-fake-video-capture=path.y4m`.

## See also

- Full guide with examples: `prompts/guides/browser-tooling.md`
- `playwright-e2e-testing` skill — writing the actual deterministic tests
