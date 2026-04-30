---
name: browser-tooling
description: Pick the right browser/UI tool for the job — when the user reports a UI bug, asks you to verify a deployed page, wants WebRTC/Daily testing, or asks for E2E test coverage. Routes between Playwright tests, agent-browser, pinchtab, Playwright MCP, Chrome DevTools MCP, and Stagehand.
---

# Browser Tooling Router

The dotfiles install five categories of browser/UI tools with different cost shapes. Use this skill to pick the cheapest one that does the job, and to remember what's available.

## Decision tree

**"Look at this page" / "Did the deploy work?" / smoke check** → **Tier 2 CLI**
- `agent-browser` (Vercel Labs) — ~200–400 tokens/page. First choice for one-shot inspection.
- `pinchtab` — ~800 tokens/page via accessibility tree. HTTP API, good for short interactive sessions: `pinchtab serve --port 9867` then `curl localhost:9867/snapshot`.
- Both shell out — no per-session MCP context cost.

**"Reproduce a bug, click around, screenshot it"** → **Tier 3a Playwright MCP**
- Loaded MCP. ~13.7k context. Drive a real headed/headless browser.
- Use when the task needs real input simulation, persistent state across steps, or WebRTC (`--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream`).

**"Why is this slow / what error fired / network looks wrong"** → **Tier 4 Chrome DevTools MCP**
- ~18k context. Network, console, perf traces. Can attach to a running Chrome.
- Don't load alongside Playwright MCP unless both are genuinely needed — context tax stacks.

**"Catch this regression forever"** → **Tier 1 Playwright tests**
- Free per run. Write tests in the project's `web/tests/e2e/`. Use Daily fake-media flags for WebRTC.
- After root-causing a bug with a Tier 3/4 MCP, write a Tier 1 test so the bug can never silently regress.

**"Long agentic flow that spans 20 screens"** → **Tier 5 Stagehand (per-project)**
- `@browserbasehq/stagehand` — natural-language `act`/`extract`/`observe`. Selectors don't rot.
- Costs LLM tokens per test run. Reach for it only when selector-based tests rot faster than they catch bugs.
- Install per-project: `npm install @browserbasehq/stagehand` (not a global tool).

## Token budget reference

| Tier | Tool | Cost shape |
|------|------|------------|
| 1 | Playwright tests in CI | 0 / run (one-time write cost) |
| 2 | agent-browser CLI | ~200–400 tokens / page |
| 2 | pinchtab CLI | ~800 tokens / page |
| 3a | Playwright MCP | ~13.7k context loaded |
| 4 | Chrome DevTools MCP | ~18k context loaded |
| 5 | Stagehand | LLM tokens / test run |

## Workflow patterns

**Bug report → permanent test:**
1. Reproduce with Playwright MCP (Tier 3a).
2. If perf/network smells → switch to Chrome DevTools MCP (Tier 4).
3. Once root-caused, write a Playwright test (Tier 1) so it's protected forever.

**"Check the page looks right":**
- Default to `agent-browser` (Tier 2). Don't load an MCP for this.

**WebRTC / Daily.co:**
- Tier 1 or Tier 3a. Both support `--use-fake-device-for-media-stream` via Chromium launch args.
- Reference: Daily.co "headless robot" pattern — `--use-file-for-fake-audio-capture=path.wav`, `--use-file-for-fake-video-capture=path.y4m`.

## Loading MCPs on-demand

Playwright MCP and Chrome DevTools MCP are configured in `agents/shared/mcp-servers.json`. They load with each Claude Code session. If they're not needed for a session and you want to save context, the user can disable per-session via `MCP_SKIP=playwright,chrome-devtools` before launch, or use `claude mcp disable`.

## See also

- Full guide with examples: `prompts/guides/browser-tooling.md`
- Existing skill: `playwright-e2e-testing` (covers writing the actual Tier 1 tests)
