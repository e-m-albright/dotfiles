---
name: agentic-e2e-debugging
description: Drive a full-stack feature end-to-end as an agent — test by clicking, watch logs, fix what surfaces, re-test. Use when the user asks "test the full flow", "exercise X start to finish", or "is the lifecycle working." Goes deeper than browser-tooling. Covers service logs, auth fixtures, hot-reload chains, and the scout→escalate→commit→reload loop.
---

# Agentic E2E Debugging

The browser-tooling skill picks the right *single* tool. This skill is about
running an entire **full-stack feature lifecycle** with multiple tools in a
loop: drive the UI, watch the logs, identify the bug, fix it, reload the
service, re-drive the UI. Use it when the task is "verify the whole flow"
rather than "look at one page."

## Core loop

```
scout (agent-browser) → break early, cheap signals
  ↓
read service logs while UI runs
  ↓
identify root cause (don't shotgun fixes — see systematic-debugging)
  ↓
fix code (small, focused diff)
  ↓
commit + fast-forward main (or whatever triggers reload)
  ↓
re-drive the same flow
  ↓
... until the lifecycle completes clean ...
  ↓
write Tier-1 lock-ins (Playwright tests) for the bugs you fixed
```

Each loop iteration should produce **one commit, one specific fix, one
verification.** Resist the urge to bundle multiple speculative fixes — when
something later breaks, you'll waste cycles untangling which change caused
which symptom.

## Tooling layout (a typical full-stack shape)

A typical full-stack app has 3–4 services and 2–3 log streams to watch.
Substitute your own process manager / log paths; the shape generalizes:

| Layer | Process | Log path | Hot-reload? |
|---|---|---|---|
| Web (Vite) | `just dev web` | `logs/web/console.log` | ✅ HMR |
| API (Rust) | `just dev api` | `logs/api/console.log` | ❌ rebuild required |
| Agents (Python) | `just dev agents --reload` | `logs/agents/console.log` | ✅ uvicorn `--reload` |
| Workers (Rust) | `just dev work` | `logs/work/console.log` | ❌ rebuild required |

**Most useful single log:** the agents/pipeline log if the bug touches the
LLM/pipeline path, the API log if it touches data persistence or auth. Keep
them in two terminal panes if you can.

When you change compiled code (Rust, Go), the running binary won't pick it up
unless the stack is running under a file watcher. Two control flows to know:

1. **Watch mode (recommended for agent-driven dev loops):** ask the user
   to start the stack with watch + reload flags (e.g.
   `just dev local --watch --reload`). `--watch` runs the compiled API under
   `cargo-watch` (or equivalent); `--reload` runs the agents service under
   `uvicorn --reload`; Vite is HMR by default. With this set up, every
   commit + ff to main automatically reloads everything affected. No
   human restart needed.

2. **Stable mode + bounce:** when the user is running the stack without
   watch (e.g., for demos), use a targeted bounce
   (`just dev bounce <api|agents|web|all>`) to SIGTERM one service by port.
   If the bounced service was started under watch, it auto-respawns;
   otherwise the user re-runs `just dev <api|agents|web>` in their terminal.

Either way: batch related fixes into one commit so the loop runs cleanly.

## Auth fixture

Browser-driven testing needs a logged-in account. Provision a deterministic
test user and write its credentials into the env the app reads:

```bash
just dev seed-test-user
# → creates a known test account (e.g. test+e2e@<app>.local) with a fixed password
# → upserts TEST_USER_EMAIL / TEST_USER_PASSWORD into the .env file(s)
```

Make it idempotent — re-runnable anytime. Use these in `agent-browser` via the
login flow; a fresh session every Chrome restart costs ~3 actions.

**Never inject another user's session cookie from the DB into the
browser.** That's impersonation; a well-built sandbox will (correctly) refuse
it. If auth state is lost, log in cleanly with the test fixture.

## Service controls the agent can use

| Need | Command | Notes |
|---|---|---|
| Start full stack with hot-reload | `just dev local --watch --reload` | Recommended for agent-driven dev. Vite HMR + uvicorn `--reload` + cargo-watch. |
| Free a port without taking the rest down | `just dev bounce <api\|agents\|web\|all>` | SIGTERM, fallback SIGKILL. Watcher (if running) respawns. |
| Restart the whole stack from scratch | `just dev restart` | Clear logs + relaunch. |
| Provision a test account + write `.env` | `just dev seed-test-user` | Idempotent. |
| Check service health | `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/api/health` | 200 = up. |

The agent shouldn't `kill` arbitrary processes by name — a good `bounce`
resolves the listener via `lsof -ti :PORT` so it never grabs an unrelated PID.

## Tool selection inside the loop

This is the routing logic from `browser-tooling`, but specialized for
*lifecycle* work:

### Drive the UI

- **Default: agent-browser.** ~200–400 tokens/page, no MCP context tax.
  Use `open`, `snapshot`, `click @e<n>`, `keyboard type`, `eval`.
- **Escalate to Playwright MCP** when:
  - `agent-browser`'s synthetic clicks no-op (Svelte 5 / React 19 forms
    sometimes don't react to synthetic events).
  - You need to maintain state across many steps and want richer snapshot
    + console + network in one tool.
  - You need real WebRTC media (fake-media flags).
- **Don't reach for Chrome DevTools MCP** unless you need network/perf
  beyond what `agent-browser network requests` shows.

**Svelte 5 gotcha (write this on your hand):** `agent-browser fill <ref>
<text>` sets `input.value` but doesn't dispatch the synthetic `input` event
Svelte 5's `bind:value` listens for. Symptom: text appears in DOM, but Send
buttons stay disabled and nothing reactive updates. Use `agent-browser focus
<ref>` then `agent-browser keyboard type <text>` instead.

**Stale ref hazard:** `@e5` is scoped to the snapshot it came from. After
any navigation, re-snapshot before clicking. Otherwise you may land on an
unrelated element on the new page (canonical mistake: clicking a stale
`@e5` after a route change and ending up in a settings panel you didn't
ask for).

### Read the logs

```bash
# Tail a specific service (use your project's log path)
tail -200 logs/agents/console.log

# Filter by session ID (most useful pattern for lifecycle bugs)
grep "<session-uuid>" logs/agents/console.log | grep -iE "error|stage|pipeline"

# Filter by request_id when chasing a single SSE stream
grep "<request-id>" logs/agents/console.log | tail -40
```

Don't pipe `tail -f`. Use repeated bounded `tail -200 | grep` calls — easier
to scope and cheaper to read.

When the agent service is on `--reload`, `WatchFiles detected changes` lines
in the log confirm your edit landed. If you don't see that line, the
running service is watching a different checkout (common when working in a
git worktree — main is what's running, your edits are in the worktree, ff
to main to reach the watcher).

### Network + console for the browser

```bash
agent-browser console            # last ~40 console lines
agent-browser network requests   # last ~40 network calls
agent-browser network requests --filter "/api/chat"
```

To capture a request body that's already gone past, install a fetch
interceptor proactively *before* triggering the action:

```js
agent-browser eval "
window.__lastReq = null;
const orig = window.fetch;
window.fetch = async (url, opts) => {
  if (typeof url === 'string' && url.includes('/api/X')) {
    window.__lastReq = { url, body: opts?.body };
  }
  return orig(url, opts);
};
'installed'
"
# trigger the action via the UI, then:
agent-browser eval "JSON.stringify(window.__lastReq)"
```

## Anti-patterns (lessons from real lifecycle runs)

- **Shotgun fixes.** When a single click produces three errors, pick one,
  fix it, re-run. Don't speculatively patch all three. The downstream
  errors are often symptoms of the upstream one.
- **Skipping log reads.** Every "the chat is broken" investigation should
  start with `grep -iE "error|401|stage" logs/agents/console.log | tail -40`.
  The first thing you do is read the last error. Always.
- **Patching prompts to fix structural bugs.** If the LLM is double-firing
  text alongside a tool call, that's a prompt-engineering tweak that may
  or may not stick (model behavior is stochastic). Prefer structural fixes
  (suppress one of the messages in the broadcaster) when the prompt fix is
  unreliable.
- **Modifying baselines just to commit.** If a change pushes a baseline
  over its ceiling, ask whether the addition is *real value* (legitimate
  prompt content, new feature) — bump the baseline. If it's noise (extra
  imports, dead code), trim. Never trim genuine code to game the score.
- **Restarting a compiled service without batching.** Each rebuild costs the
  user a context switch and ~30s. Batch related fixes into one commit
  before asking for a restart.

## Commit / merge / reload pattern (worktrees)

When working in a git worktree, the running services watch the **main
checkout**, NOT the worktree. Edits in the worktree don't reload until you
commit and fast-forward main:

```bash
# In the worktree:
git add -u && git commit -m "fix: ..."
cd <main-checkout> && git merge --ff-only <worktree-branch>
# Then, depending on what the user has running:
#   --watch + --reload mode: nothing else to do; watchers auto-reload.
#   stable mode: `just dev bounce api` (or agents/web) to free the port.
```

This is **the** most common reason "my fix isn't taking effect" — the
running watcher is on a different tree than the one you edited.

## Logging gaps — fill them as you find them

If a bug went undiscovered for weeks because of a *silent* code path
(early `return`, swallowed exception, no breadcrumb when a frame is
dropped), add a debug-level log line as part of the fix. The next person
who hits a similar issue should be able to find it from the log instead
of the source. Real example: a frame handler had a silent source-guard
`return` that masked a typed-frame bug for weeks; a single
`_log.debug("frame_dropped_unknown_source", ...)` would have surfaced it on
day 1.

The bar: every silent drop or early-exit branch should leave a breadcrumb
unless it's truly a hot-path noise filter (and then add a counter, not a
log).

## When to write the Tier-1 test

After you root-cause a bug, write a Playwright integration test that
exercises the same path. The bar:

- The test fails before your fix.
- The test passes after your fix.
- The test names the bug ("anonymous_join_returns_no_401",
  "warmup_transition_does_not_double_speak").

Don't write speculative tests. Tests come from real bugs with real
reproducers.

## Skill stack-up

- `browser-tooling` — pick the right single tool for one job.
- `systematic-debugging` — root-cause discipline (don't
  shotgun, reproduce first, hypothesize, test).
- `verification-before-completion` — never claim a fix works
  without seeing the verified output.
- `playwright-e2e-testing` — write the Tier-1 lock-in tests.
- This skill — runs the loop that ties all four together.
