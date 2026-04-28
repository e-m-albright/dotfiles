# Browser Tooling for AI Agents

> **Last reviewed**: 2026-04-28 — Refresh when new browser-automation tools mature past 6 months.

A tiered system for inspecting, testing, and debugging UIs from an AI agent. Pick the cheapest tier that does the job.

---

## The five tiers

| Tier | Tool | Job | Cost shape |
|------|------|-----|-----------|
| **1** | Playwright tests in CI | Regression net | 0 / run (one-time write) |
| **2** | `agent-browser` CLI | Token-cheap "look at this page" | ~200–400 tokens / page |
| **2** | `pinchtab` CLI / HTTP | Accessibility-tree extraction | ~800 tokens / page |
| **3a** | Playwright MCP | Active debugging, WebRTC, real input | ~13.7k context loaded |
| **4** | Chrome DevTools MCP | Network/console/perf forensics | ~18k context loaded |
| **5** | Stagehand (per-project) | Long agentic flows, selector-resilient | LLM tokens / run |

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

## Tier 3a — Playwright MCP (on-demand)

```jsonc
// agents/shared/mcp-servers.json
"playwright": {
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest"],
  "targets": ["claude", "cursor", "codex"],
  "profiles": ["personal", "work"]
}
```

**Reach for it when**:
- Bug reproduction needs real input simulation across multiple steps.
- Testing WebRTC flows that need actual `getUserMedia`.
- The Tier 2 CLIs aren't giving enough fidelity.

**Skip it when**: A simple "check the page" task. Tier 2 is cheaper.

---

## Tier 4 — Chrome DevTools MCP (on-demand)

```jsonc
"chrome-devtools": {
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp@latest"],
  "targets": ["claude", "cursor", "codex"],
  "profiles": ["personal", "work"]
}
```

**Specialist for**: "Why is this slow / what error fired / network looks wrong / attach to my live Chrome."

**Don't load alongside Playwright MCP** unless both are genuinely needed — they stack to ~32k of context.

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
2. **Tier 2** (`agent-browser`): can I see it from a quick page snapshot? If yes, often enough info to root-cause.
3. **Tier 3a** (Playwright MCP): if I need to interact, click around, simulate state. Reproduce the bug.
4. **Tier 4** (Chrome DevTools MCP): if it's a perf/network issue. Get the trace.
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
