# Browser Tooling for AI Agents

> **Last reviewed**: 2026-06-09 — dropped the browser MCP servers (Playwright MCP, Chrome DevTools MCP) in favor of the CLI layer; refresh when new agent-browser tools mature past 6 months.

A tiered system for inspecting, testing, and debugging UIs from an AI agent. Pick the cheapest tier that does the job. **The endorsed stack: Playwright + agent-browser for ~90% of work; pinchtab on standby for human-in-the-loop authed sessions.** No browser MCP servers are loaded — the CLI layer gives the same agent-native control (a11y snapshots, persistent session) without an always-on context tax.

The tools sit at **different layers**, not in competition: Playwright is the automation *framework* (write code; testing/scraping foundation); `agent-browser` is the agent-native control *CLI* (a11y text, token-cheap, shells out); `pinchtab` is a control *server* (persistent, logged-in, watchable browser). CDP is the low-level protocol they all talk to Chrome through.

---

## The tiers

| Tier | Tool | Job | Cost shape |
|------|------|-----|-----------|
| **1** | Playwright tests in CI | Regression net, deterministic scrape | 0 / run (one-time write) |
| **2** | `agent-browser` CLI | Default agent browsing / "look at this page" | ~200–400 tokens / page · no MCP tax |
| **2b** | `pinchtab` CLI / HTTP | Human-in-the-loop on a logged-in browser | ~800 tokens / page · no MCP tax |
| **5** | Stagehand (per-project) | Long agentic flows, selector-resilient | LLM tokens / run |
| ~~3a~~ | ~~Playwright MCP~~ | dropped — agent-browser covers it | was ~13.7k always-on |
| ~~4~~ | ~~Chrome DevTools MCP~~ | dropped — launch ad-hoc if ever needed | was ~18k always-on |

---

## Tier 1 — Playwright tests in CI

**Goal**: Catch regressions automatically, forever, free per run.

```bash
# Inside the project
bunx playwright install chromium
bunx playwright test
```

**WebRTC / Daily.co setup** — Daily's "headless robot" pattern uses Chromium launch flags:

```ts
// playwright.config.ts
use: {
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',       // skip permission prompt
      '--use-fake-device-for-media-stream',   // test-pattern video
      '--use-file-for-fake-audio-capture=fixtures/audio.wav',
      '--use-file-for-fake-video-capture=fixtures/video.y4m',
    ],
  },
}
```

**When to write a Tier 1 test**: After root-causing a bug with a Tier 3/4 MCP. The test ensures the bug stays fixed.

---

## Tier 2 — Token-cheap CLIs

### agent-browser

```bash
# Already installed globally via dotfiles (macos/brew.sh)
agent-browser open https://example.com
agent-browser inspect "button:has-text('Submit')"
agent-browser screenshot --output /tmp/page.png
```

**Best for**: "Did the deploy land? What does this study look like? Smoke-check this page."

### pinchtab

```bash
# Already installed globally via dotfiles
pinchtab serve --port 9867 &
curl localhost:9867/snapshot?refs=role
curl -X POST localhost:9867/click -d '{"ref":"e42"}'
```

**Best for**: Short interactive sessions where accessibility-tree extraction is enough.
**Caveat**: Created Feb 2026 — relatively young. Watch for sustained maintenance.

---

## Tier 2b — pinchtab (human-in-the-loop standby)

```bash
pinchtab serve --port 9867
curl localhost:9867/snapshot          # accessibility-tree snapshot
```

**Reach for it when**: agent-browser's headless model isn't enough — you need a **persistent, visible, logged-in** browser the agent drives while you watch/intervene (authed sites, multi-step flows you supervise). Pinchtab's distinctive edge over agent-browser is exactly that human-in-the-loop, stay-logged-in session.

**Skip it when**: a one-shot inspection or an unattended flow — agent-browser is cheaper and simpler.

---

## Dropped: browser MCP servers (2026-06-09)

Playwright MCP and Chrome DevTools MCP were removed from `agents/shared/mcp-servers.json`. An MCP server taxes **every** session's context with its tool schemas whether you browse or not; the agent-native value (structured a11y snapshots + a persistent session) is already provided by `agent-browser` (CLI) and `pinchtab` (server) on demand, at zero standing cost.

If you ever need DevTools-style perf/network/console forensics, launch it **ad-hoc** for that one session and drop it after — don't make it standing:

```bash
npx chrome-devtools-mcp@latest         # one-off, not in the managed config
```

Note: Playwright-the-*framework* (Tier 1 tests) is a different layer than Playwright-*MCP* (agent control). We keep the framework, drop the MCP.

---

## Tier 5 — Stagehand (per-project)

```bash
# Inside the project
npm install @browserbasehq/stagehand
```

```ts
import { Stagehand } from '@browserbasehq/stagehand';

const stagehand = new Stagehand({ env: 'LOCAL' });
await stagehand.init();
await stagehand.page.goto('https://example.com');
await stagehand.page.act('click the submit button');
const data = await stagehand.page.extract({ instruction: 'get the order total' });
```

**Reach for it when**: A test flow spans many screens where the UI redesigns frequently and selector-based tests rot faster than they catch bugs.

**Skip it when**: Selector-based Playwright tests are still working — Stagehand costs LLM tokens per run.

---

## Common workflow

1. User reports a UI bug.
2. **Tier 2** (`agent-browser`): can I see it from a quick page snapshot? If yes, often enough to root-cause.
3. **Tier 2b** (`pinchtab`): if I need a persistent, watchable, logged-in browser to reproduce. Click around, simulate state.
4. **Ad-hoc** (`chrome-devtools-mcp` for one session): only if it's a perf/network issue needing a trace.
5. **Tier 1** (Playwright test): write a regression test once root-caused. Now it's protected forever.

For greenfield long flows, consider **Tier 5** (Stagehand) instead of Tier 1 if the UI is volatile.

---

## What we skip and why

- **Claude in Chrome / browser extensions**: can't run headless, can't run in CI.
- **Browserbase cloud (Stagehand managed)**: optional. Only if we hit captcha/anti-bot or need cross-machine session replay. Local Stagehand covers most needs free.
- **Browser-use** (the SDK): overlaps with Stagehand. Pick one.

---

## Sources

- *Playwright vs. Chrome DevTools MCP: Driving vs. Debugging* — covers the cost/specialty split
- *I Tested Every Browser Automation Tool for Claude Code* — token benchmarks
- *Daily.co: How to make a headless robot to test WebRTC* — fake-device flags
- *Stagehand* — Browserbase, https://github.com/browserbase/stagehand
- *agent-browser* — Vercel Labs, https://agent-browser.dev
- *pinchtab* — https://github.com/pinchtab/pinchtab
