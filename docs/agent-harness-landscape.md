# Agent Harness Landscape — Watch

**Status:** OPEN / ongoing survey. Not an active build — a tracked view of the
coding-agent tooling landscape and where our own harness ambitions sit.

**Last surveyed:** 2026-07-20 · **Next review cue:** when a tracked tool ships a
step-change, or roughly quarterly.

**Project this belongs to:** *own our coding surface.* The install-manifest side
of this watch lives in [`macos/packages.toml`](../macos/packages.toml) (the
`AI CLI Tools` / `IDE` sections). This doc is the reasoning and capability view.

---

## The bet

The long-term aim is to **own the coding harness** — the layer between us and the
model — rather than rent it. Owning it buys transparency (nothing injected behind
your back), stability (your workflow doesn't break when a vendor reshapes their
prompts), and eventually **privacy/control** by pairing a self-owned harness with
a self-hosted open model. That last part is a different problem for a different
day (see [local-llm-stack.md](local-llm-stack.md)) — the fantasy endpoint is
wiring a minimal harness like Pi to a Kimi K2/K3-class open model we control.

This is explicitly **not** a bet on agent velocity for its own sake.

## Current stance (2026-07-20)

**Decision: stay on Codex + Claude Code directly, on their subscriptions.** Best
bang-for-buck right now. Rationale:

- **Subscription economics win at personal scale.** Paying per-token API for a
  self-run harness is economically worse for our usage than a flat Claude/ChatGPT
  subscription that's already doing a good job. Pay the subscription, use the
  tool, don't maintain the tool.
- **Pi is attractive but not now.** Tuning Pi into a preferred surface is roughly
  a weekend project; the real cost is the ongoing **maintenance tax** of keeping a
  hand-built harness current. Deferred, not rejected.
- **No armies/factories of agents.** Large fleets of concurrent agents are the
  wrong bet for us — we won't make it. One-to-a-few observable agents, max.

### Guiding principles

- **Velocity is gated by human comprehension, not agent count.** Spinning up more
  concurrent agents doesn't raise real throughput once you can't hold what they're
  doing in your head — it lowers it. More running things makes comprehension
  worse, not better.
- **Maintenance tax is the true cost of owning the bleeding edge.** A self-owned
  harness means every brilliant idea that lands in some other tool becomes work to
  port or forgo.
- **Distance from the frontier is a feature, not a bug.** A harness that
  intentionally separates you from the week-to-week churn is doing you a favor.
  Pi's minimalism is this stance made concrete.
- **Prefer the smallest thing that holds.** Higher-level abstractions that hide
  the agent loop (agent inboxes, orchestrators) are off the table while they hide
  more than they reveal.

---

## How to read the landscape — tiers

Tools are grouped by **how much they hide** — which is the axis that matters for
the "own your surface" goal.

| Tier | What it is | Hides | Our posture |
|---|---|---|---|
| **1 — Terminal harness** | Agent loop in your terminal; you see every tool call | Least | Candidates for a self-owned surface |
| **2 — Editor-integrated** | Agent embedded in an IDE/editor | Some (editor + cloud) | Useful, but not "ours" |
| **3 — Orchestration / inbox** | Manages fleets of agents, worktrees, or an "agent inbox" | Most | Deliberately avoided for now |

---

## Catalog

Everything on the watch list, grouped by tier. The deep-profiled comparison set
(Tier 1, seven tools) has a full capability matrix below; the additions are
catalogued at the positioning level and flagged for later deep-profiling.

### Tier 1 — terminal harnesses

| Tool | Lineage | License | Positioning / why it's here |
|---|---|---|---|
| **Pi** | Mario Zechner → earendil-works | MIT | The minimal, transparent, self-extensible core. Our primary "own it" candidate. Sub-1k-token prompt, 4 tools, deep extension API, 3-ecosystem subscription auth. |
| **Oh My Pi** (`omp`) | can1357 fork of Pi | MIT | Batteries-included Rust reimplementation. Already builds most of what base Pi omits (LSP, DAP, subagents, hash-anchored edits) and *inherits* existing `.claude`/`.codex` configs. The "already assembled" version of the Pi bet. |
| **Claude Code** | Anthropic | proprietary | Current daily driver. Subscription (Claude Pro/Max). Mature, deep hooks/skills/subagents/sandbox. |
| **Codex** | OpenAI | Apache-2.0 | Current daily driver. ChatGPT-subscription auth. Real OS sandboxing, V4A `apply_patch`, MCP client *and* server, cloud/async. |
| **Amp** | Sourcegraph | proprietary | Frontier-pushing, heavily built-out. Mode-dial instead of model choice; Orbs remote agents; Oracle/Librarian sub-agents. Watch, not adopt. |
| **Droid** | Factory.ai | proprietary | Frontier-pushing. Model-routing philosophy, Missions orchestration, broadest surface (CLI/IDE/Web/Slack/Linear/Jira). Top Terminal-Bench claims. Watch, not adopt. |
| **OpenCode** | sst (Anomaly) | MIT | Vendor-neutral, 75+ providers, client/server + SDK, ACP everywhere, reads `CLAUDE.md`. The open-source neutral option. |
| **Aider** | Paul Gauthier | Apache-2.0 | The OG minimal git-native terminal pair-programmer. BYOK, repo-map, commit-per-change, maintains the Polyglot leaderboard we already cite. Closest philosophical cousin to Pi's minimalism. *Deep-profile pending.* |
| **Gemini CLI** | Google | Apache-2.0 | Open-source terminal agent, generous free tier on Gemini. **Largely superseded by Antigravity** (Google's agentic IDE) — tracking mainly for the local-model/free-tier angle. *Deep-profile pending.* |

### Tier 2 — editor-integrated agents

| Tool | License | Positioning |
|---|---|---|
| **Cursor** | proprietary | AI-native VS Code fork (Anysphere). Subscription. Strong inline + agent modes; increasingly pushing **cloud/background agents** (drifts toward Tier 3). Previously evaluated and tombstoned in our manifest. |
| **Cline** | open source | Autonomous coding agent as a VS Code extension. BYOK, MCP-heavy, plan/act split. Notable as an open, editor-embedded option. *Not host software — lives in the editor, so catalogued here, not in the manifest.* |
| **Antigravity** (IDE) | proprietary | Google's agentic IDE; the successor surface to Gemini CLI. Introduces **agent-inbox / agent-manager** UX — see Tier 3 note. Tombstoned in our manifest. |

### Tier 3 — orchestration / multiplexers / agent inboxes

These manage *fleets* of agents. Explicitly **avoided for now** — they hide the
agent loop and lean into the concurrency-as-progress framing we're skeptical of.

| Tool | Positioning | Our take |
|---|---|---|
| **Conductor** | Mac app that runs many Claude Code agents in parallel across git worktrees | Too much fleet, too little comprehension for us. Tombstoned. |
| **cmux** | Terminal workspace/multiplexer for agent sessions | Didn't beat Ghostty + Zellij session control. Tombstoned. |
| **Cursor agents** | Cursor's cloud/background agent surface | Heavy; hides execution. Not our direction. |
| **Antigravity agent inbox** | Manage/triage a queue of autonomous agents | Hides far too much right now. Firmly not going this way. |

---

## Capability matrix — deep-profiled set (2026-07-20)

Legend: **●** native / first-class · **◐** partial / limited / via-IDE ·
**◈** only by building or installing an extension · **○** absent (by design or unbuilt).

A richer, theme-aware visual version of this matrix was generated as a companion
report; this table is the durable source of truth.

| Capability | Pi | Oh My Pi | Claude Code | Codex | Amp | Droid | OpenCode |
|---|---|---|---|---|---|---|---|
| **License** | MIT | MIT | proprietary | Apache-2.0 | proprietary | proprietary | MIT |
| **Implementation** | TS/Node | Rust+TS | TS/Node | Rust | TS/Node | proprietary | TS/Bun |
| **BYOK breadth** | ● 20+ | ● 40+ | ◐ Anthropic-centric | ◐ OpenAI+local | ○ none | ● multi+custom | ● 75+ |
| **Subscription auth** | ● Claude+ChatGPT+Copilot | ● Anthropic/Gemini/Copilot | ● Claude Pro/Max | ● ChatGPT | ◐ ChatGPT link | ○ own plan | ○ BYOK only |
| **Per-role model routing** | ◐ | ● 5 roles | ◐ | ● per-subagent | ● mode | ● complexity | ◐ |
| **Edit primitive** | string | hash-anchored | string | V4A apply_patch | string | Edit/ApplyPatch | string+apply_patch |
| **Stale-edit safety** | ◐ read-first | ● reject-on-drift | ◐ read-first | ◐ context-anchor | ◐ | ◐ | ◐ |
| **Background shell** | ○ (tmux) | ● | ● | ● | ◐ | ◐ | ● |
| **AGENTS.md / CLAUDE.md** | ● | ● reads 8 fmts | ● | ● | ● +globs | ● | ● +CLAUDE fallback |
| **Auto-compaction** | ● | ● | ● | ● | ◐ | ◐ | ● |
| **Cross-session memory** | ○ DIY | ● retain/recall | ◐ | ◐ | ◐ | ◐ | ○ |
| **Built-in subagents** | ○ tmux/ext | ● task+smol | ● Agent+types | ● worker/explorer | ● auto | ● custom droids | ● explore/scout |
| **Multi-agent orchestration** | ◈ ext | ● swarm DAG | ● Workflow | ● threads+CSV | ◐ Orbs | ● Missions | ◐ task |
| **Parallel worktree isolation** | ○ | ● COW | ● worktree | ◐ | ◐ | ● | ◐ |
| **Background / async tasks** | ○ | ● | ● | ● +cloud | ● Orbs | ● Computers | ◐ Actions |
| **Plugins / custom tools** | ● deep | ● | ● +MCP | ● | ● | ● | ● |
| **Lifecycle hooks** | ● 30+ | ◐ stream-rules | ● | ● | ◐ 5 | ● | ● |
| **Skills (SKILL.md)** | ● | ● +8 fmts | ● originated | ● | ● | ● | ● +.claude |
| **MCP client** | ◈ build ext | ● +inherits cfg | ● | ● | ● | ● | ● |
| **MCP server (expose self)** | ○ | ◐ | ◐ serve | ● mcp-server | ○ | ○ | ○ |
| **Approval / permission modes** | ○ DIY | ● prompt+remember | ● modes+rules | ● policies | ◐ off-default | ● autonomy | ● allow/ask/deny |
| **OS-level sandbox** | ○ | ◐ COW (not syscall) | ● Seatbelt | ● Seatbelt/bwrap | ○ | ◐ | ○ |
| **LSP integration** | ○ | ● 14 ops | ◐ via IDE | ○ | ○ | ○ | ◐ 28 servers |
| **Semantic rename** | ○ | ● | ○ | ○ | ○ | ○ | ◐ |
| **DAP live debugging** | ○ | ● 28 ops | ○ | ○ | ○ | ○ | ○ |
| **Browser / computer use** | ○ | ● CDP+Electron | ◈ via MCP | ● computer use | ◐ screenshot | ○ | ○ |
| **IDE plugins** | ○ RPC only | ◐ Zed/ACP | ● VS Code+JB | ● VS Code+JB+Xcode | ● 4 editors | ● VS Code+JB | ● VS Code+ACP |
| **ACP (editor protocol)** | ◐ | ● Zed | ◐ Zed | ○ | ● Zed | ○ | ● Zed/JB/Nvim |
| **Cloud / async agents** | ○ | ○ ssh only | ● web+Actions | ● Codex cloud | ● Orbs | ● Computers | ◐ Actions |
| **GitHub PR review bot** | ○ gist | ◐ pr:// | ● @claude | ● @codex review | ◐ push-branch | ● @droid | ● /oc |
| **Git / PR workflow** | ○ gist | ● commit-split | ● | ● | ● push-branch | ● | ● /undo(git) |
| **Cost / token tracking** | ● footer | ◐ | ● /cost | ● /usage | ● usage | ● dash | ● stats |
| **Telemetry (OTel)** | ◐ install-ping | ◐ fork | ● | ● opt-in | ◐ | ◐ | ◐ local |
| **Session branch / undo** | ● tree/fork | ● checkpoint/rewind | ● resume/rewind | ● resume/fork | ◐ | ◐ fork | ● undo/redo |
| **Config format** | JSON `.pi/` | YAML `~/.omp/` | JSON settings | TOML config | JSON settings | JSON `.factory/` | JSON opencode |

### Pi vs Oh My Pi — the pair worth knowing

Same thesis ("the model is the moat, the harness is the bridge"), opposite
defaults:

- **Base Pi** — a tiny transparent core you own and build on. Standout perk:
  three-ecosystem subscription auth (Claude Max + ChatGPT + Copilot) in one tool,
  plus 20+ BYOK and local `llama.cpp`. Cost: a rebuild tax for anything beyond
  read/write/edit/bash.
- **Oh My Pi** — a ~55k-LOC Rust fork (single maintainer, young) that has already
  built the rebuild list and **inherits your existing `.claude`/`.codex`/`AGENTS.md`/MCP
  config** natively. The "already assembled" path.

**Key realization:** the "what must I rebuild?" question is really a *base-Pi*
question. Pick Oh My Pi and most of it evaporates — but you take on a large
opinionated fork instead of a small core you own.

### If we ever migrate Codex/Claude Code → base Pi: the rebuild list

Ordered by pain. This is the deferred work, captured so future-us doesn't
re-derive it.

| Severity | What we'd lose | Pi's answer | In Oh My Pi? |
|---|---|---|---|
| **Critical** | Sandbox + approval gating | none built-in; write a `tool_call` hook or run in Docker/Gondolin. **Do first.** | Partial (prompts + COW, no syscall sandbox) |
| **High** | MCP servers | write/install an MCP extension | Yes (+inherits config) |
| **High** | Subagents / orchestration | tmux fan-out or thin extension | Yes (task/swarm/hub) |
| **High** | Cloud/async + PR-review bot | not locally replicable — keep Codex/CC for this | No |
| **Medium** | Browser / computer use | custom extension | Yes |
| **Medium** | Plan mode / to-dos | `PLAN.md` file pattern | Partial |
| **Medium** | IDE / ACP | RPC/JSON embedding, no shipped plugin | Yes (Zed/ACP) |
| **Medium** | Git / PR workflow | bash or extension | Yes |
| **Low** | LSP / semantic rename | *not a regression* — Codex/CC lack it too | Yes |
| **Low** | DAP debugging | *nobody but Oh My Pi has it* | Yes |

---

## Open questions / to-do (tracked)

- [ ] **Deep-profile the additions** to matrix parity: Aider, Gemini CLI, Cline,
      Cursor (agent surface), plus Conductor/cmux positioning detail.
- [ ] **Local + open model path:** revisit wiring a minimal harness (Pi / Oh My Pi)
      to a self-hosted Kimi K2/K3-class model for privacy/control. Blocked on the
      open-weights landscape maturing; ties into `local-llm-stack.md`.
- [ ] **Re-verify churny facts** before any decision: model IDs (Amp/Codex change
      weekly), Oh My Pi LOC/stars, "Amp subagent messaging", Pi subagent "parallel
      mode". All flagged as fast-moving.
- [ ] **Revisit the "own the harness" build** when the maintenance tax visibly
      drops (Oh My Pi stabilizes) or a genuine step-change lands. Not before.
- [ ] **Trigger to re-open the decision:** subscription economics change, a
      privacy requirement appears, or Codex/Claude Code degrade.

## Sources (primary, 2026-07)

- Pi — [badlogic/pi-mono](https://github.com/badlogic/pi-mono),
  [design blog](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/), pi.dev
- Oh My Pi — [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi), blog.can.ac
- Codex — [openai/codex](https://github.com/openai/codex), learn.chatgpt.com/docs
- OpenCode — [sst/opencode](https://github.com/sst/opencode), opencode.ai/docs
- Amp — [ampcode.com/manual](https://ampcode.com/manual)
- Droid — docs.factory.ai
- Aider — aider.chat · Cline — github.com/cline/cline · Gemini CLI —
  github.com/google-gemini/gemini-cli · Cursor — cursor.com · Antigravity — Google
- Claude Code — first-hand feature knowledge.

*Fast-moving category — re-verify before committing to anything.*
