# AI Development Tools

> **Last reviewed**: 2026-04-17 — Refresh quarterly or when a major tool ships.

**Philosophy**: AI tools are collaborators, not replacements. Use them to multiply output, not to automate judgment.

> **Reality Check**: Developers use AI for ~60% of their work but can "fully delegate" 0% of tasks.
> AI excels at well-defined, verifiable work. Humans own architecture, context, and final decisions.

---

## Tool Selection by Task

```
                    ┌─────────────────────┐
                    │ What are you doing? │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌────────────────┐
│ Complex task  │    │ Quick iteration │    │ Full-stack MVP │
│ Multi-file    │    │ Single file     │    │ Prototype      │
│ Architecture  │    │ Debugging       │    │ Demo           │
└───────┬───────┘    └────────┬────────┘    └───────┬────────┘
        │                     │                     │
        ▼                     ▼                     ▼
   Claude Code            Cursor              bolt.new
```

---

## My Active Stack

What I actually pay for and use daily, organized by vendor.

### Local (Interactive)

Tools that run on my machine. I drive the session, review in real-time.

| Vendor | Tool | Surface | Best For |
|--------|------|---------|----------|
| **Anthropic** | Claude Code | CLI, desktop app, IDE extensions | Complex multi-file work, architecture, long-running tasks |
| **Anthropic** | Claude Desktop | Desktop app | Chat + MCP tool use, research, exploration |
| **Cursor** | Cursor | Desktop IDE | Fast iteration, inline edits, Tab completions, debugging |
| **OpenAI** | Codex CLI | CLI | Second-opinion reviews, fire-and-forget tasks |

### Cloud (Autonomous)

Agents that check out my repo from GitHub, run on the vendor's servers, and produce PRs or results asynchronously. Fire-and-forget — review the output, not the process.

| Vendor | Tool | Surface | Best For |
|--------|------|---------|----------|
| **Anthropic** | Claude Code | claude.ai/code | Autonomous tasks when away from terminal |
| **Cursor** | Background Agents | Cursor cloud | Offloading work while iterating locally |
| **OpenAI** | Codex Cloud | ChatGPT | Parallel sandboxed tasks, drafting PRs |
| **Google** | Jules | Web (jules.google.com) | Async issue-to-PR against GitHub repos |

### How I Use Them Together

```
Interactive session (primary workflow):
├── Claude Code CLI — architecture, multi-file features, complex work
├── Cursor — refinement, debugging, quick edits in IDE
└── Codex CLI — cross-model review, second opinion

Fire-and-forget (async delegation):
├── Claude Code Cloud — tasks I'd run locally but I'm away
├── Cursor Background Agents — offload while doing other IDE work
├── Codex Cloud — parallel tasks, draft PRs for review later
└── Jules — backlog issues, straightforward GitHub PRs
```

> **Rule of thumb**: Start interactive. Delegate to cloud agents only for well-scoped, verifiable tasks — the kind where you can review the PR diff and know if it's right.

---

## AI Coding Assistants

### Tier 1: Primary Tools

| Tool | Best For | Strength | Trade-off |
|------|----------|----------|-----------|
| **Claude Code** | Complex, multi-file work | Agentic (hours-long autonomous runs), MCP integration | Slower generation, needs context setup |
| **Cursor** | IDE-integrated work | Fast iteration, familiar VS Code experience | Less agentic than Claude Code |

**Recommendation**: Use both. Claude Code for complex features and architecture. Cursor for rapid iteration and debugging.

### Tier 2: Alternatives

| Tool | When to Use |
|------|-------------|
| **OpenCode** | Model flexibility, mix providers, open-source CLI. TUI-first, plan/build modes. SST team. $10/mo (Zen) or BYO keys. |
| **GitHub Copilot** | Enterprise teams with GitHub integration |
| **Windsurf 2.0 (Cognition/Devin)** | Now owned by Cognition. Native Devin integration + Agent Command Center. $15-50/mo. |
| **Aider** | Lightweight CLI agent with auto git commits. Python-native, many models. Good for scripted workflows. |
| **Gemini CLI** | Google Cloud-heavy projects |

### Usage Patterns

```bash
# Claude Code: Complex autonomous work
claude "implement the user authentication system with OAuth, email verification, and session management"

# Cursor: Quick iterations in IDE
# Open file, use Cmd+K for inline edits, Tab for completions

# Combine for best results:
# 1. Claude Code for architecture decisions + initial implementation
# 2. Cursor for refinement, debugging, small changes
```

---

## Full-Stack App Builders

> **Use for**: Rapid prototyping, MVPs, demos. Not for production architecture.

| Tool | Best For | Backend | Database | Notes |
|------|----------|---------|----------|-------|
| **bolt.new** | Full-stack MVPs | Yes | Supabase | Browser-based, no setup, production-ready code |
| **Lovable.dev** | Design-focused apps | Limited | Supabase | Beautiful UI, credit-based pricing |
| **v0.dev** | React components | No | No | Vercel ecosystem, Tailwind-native |
| **Replit Agent** | Integrated platform | Yes | Yes | All-in-one, mobile app support |

### When to Use What

- **bolt.new**: Default for quick full-stack prototypes (10-20 min MVPs)
- **v0.dev**: Isolated React/Tailwind components, then adapt to Svelte
- **Lovable**: When design quality is paramount
- **Replit**: When you want everything in one platform

### Design-First Builders (Marketing Sites / Landing Pages)

These are better for **marketing sites** than app prototypes:

| Tool | Best For | Notes |
|------|----------|-------|
| **Framer** | Polished marketing sites | Designer-focused, excellent animations, CMS built-in |
| **Webflow** | Complex marketing sites | Most powerful no-code, steep learning curve |
| **Unicorn Platform** | Simple landing pages | Quick startup pages, limited customization |

> **Note**: For app UIs, Claude Code or bolt.new are better choices. These tools excel at marketing/landing pages where design polish matters more than functionality.

### Limitations

- Backend logic often needs refinement
- Complex business logic requires human review
- Auth/payments need careful validation
- Don't ship production without code review

---

## UI Generation

### For SvelteKit (Our Stack)

**Primary**: Use Claude Code for Svelte components. More reliable than specialized tools.

```bash
claude "create a dashboard component with a sidebar, header, and main content area using Tailwind CSS and shadcn-svelte"
```

**Secondary**: v0.dev for React inspiration, then manually adapt to Svelte 5 runes.

### Why Not Specialized Svelte Tools?

- Svelte-specific generators are immature compared to React
- Claude Code understands Svelte 5 runes better than most specialized tools
- Manual adaptation from React to Svelte is often faster than debugging generated Svelte code

---

## Agent Frameworks

> **For building AI-powered applications**, not for coding assistance.

### Recommended Picks

| Framework | Language | Best For |
|-----------|----------|----------|
| **PydanticAI** | Python | Single-agent tool calling, type-safe, best DX. Our default for Python. |
| **Mastra** | TypeScript | Workflow-driven agents with strict typing. Our default for TypeScript. |
| **Instructor** | Python | Structured outputs from LLMs. Not a full agent framework — pairs with any SDK. |

### Full Framework Comparison

| Framework | Language | Strengths | Weaknesses |
|-----------|----------|-----------|------------|
| **PydanticAI** | Python | Pydantic-native, type-safe, minimal abstraction, MCP support. Best DX for single-agent work. | Limited multi-agent support. |
| **Mastra** | TypeScript | From the Gatsby team. Strict typing, built-in observability (OpenTelemetry), one-command deploys to Vercel/Cloudflare/Netlify. | Younger ecosystem, TS-only. |
| **Google ADK** | Python | Multi-agent with hierarchy, built-in eval, MCP support. Works with any provider via LiteLLM. | Medium learning curve, Google-flavored API. |
| **OpenAI Agents SDK** | Python | Thin runtime, nearly matches LangGraph in benchmarks, extremely simple to get started. | Vendor lock-in (OpenAI-first), limited customizability. |
| **Agno** (prev. Phidata) | Python | Fastest agent framework. Lean, performant, good multi-agent team support, strong observability via Agent OS. | Smaller community than PydanticAI. |
| **LangGraph** | Python/TS | Graph-based workflows, most flexible orchestration, built-in eval, MCP support. | Steepest learning curve, heavy dependency chain. LangChain ecosystem can feel bloated. |
| **Strands Agents** (AWS) | Python | Lightweight, provider-agnostic. Define tools as functions, pick a model, run. Minimal overhead. | Early ecosystem, AWS-adjacent. |
| **CrewAI** | Python | Role-based multi-agent teams. Quick setup, clear mental model, wide adoption. | Debugging can be frustrating, less type-safe. |
| **DSPy** | Python | Different paradigm: optimizes reasoning pipelines through eval-driven iteration rather than manual prompts. | Research-oriented, not for typical app development. |
| **Smolagents** | Python | Minimal, code-centric agents. HuggingFace ecosystem. | Limited features, niche. |

### Decision Tree

```
What language?
├── Python
│   ├── Need structured output? → Instructor
│   ├── Need tool calling (simple)? → PydanticAI
│   ├── Need speed + minimal overhead? → Agno
│   ├── Need multi-agent (role-based)? → CrewAI or Google ADK
│   ├── Need multi-agent (graph-based)? → LangGraph
│   ├── Need minimal, provider-agnostic? → Strands Agents
│   ├── OpenAI-only, want simplicity? → OpenAI Agents SDK
│   └── Optimizing reasoning pipelines? → DSPy
└── TypeScript
    ├── Need agents + workflows? → Mastra
    └── Need multi-agent orchestration? → LangGraph.js
```

### Quick Recommendations

- **Simple agents with tools**: PydanticAI (best DX, type-safe)
- **TypeScript agents**: Mastra (strict typing, built-in observability, easy deploys)
- **Multi-agent with hierarchy**: Google ADK (enterprise-ready, good tooling)
- **Multi-agent with roles**: CrewAI (easy setup, clear mental model)
- **Speed-critical agents**: Agno (fastest runtime, lean abstractions)
- **Minimal, drop-in agents**: Strands Agents (define tools, pick model, go)
- **Complex graph workflows**: LangGraph (most flexible, steepest learning curve)
- **Eval-driven optimization**: DSPy (for research-heavy or experiment-driven work)

> **Start with PydanticAI (Python) or Mastra (TypeScript).** Add multi-agent frameworks only when single-agent + tool calling isn't enough. Google ADK is the best multi-agent option if you need hierarchy and eval.

---

## LLM Evals & Observability

> **For monitoring, evaluating, and improving AI applications** — not general app observability (see `INFRASTRUCTURE.md` for Sentry/OTel).

### Recommended Picks

| Tool | Best For | Notes |
|------|----------|-------|
| **Langfuse** | All-in-one tracing + eval. Our default. | Open-source (MIT), self-hostable, framework-agnostic. Best starting point. |
| **Braintrust** | Prompt experimentation + CI/CD evals | End-to-end: traces become eval cases in one click, GitHub Actions integration. Best for systematic prompt improvement. |
| **Logfire** | Python/Pydantic-native observability | Built by the Pydantic team. Auto-traces Pydantic validations and PydanticAI agents. Best DX if your AI stack is PydanticAI. |

### Full Comparison

| Feature | Langfuse | Braintrust | Logfire |
|---------|----------|------------|---------|
| **License** | Open-source (MIT) | Commercial (free tier: 1M spans/mo) | Commercial (free tier available) |
| **Self-host** | Yes | No | Enterprise only |
| **Tracing** | Full LLM traces, spans, scores | Full traces + proxy | OpenTelemetry-native |
| **Evals** | Custom eval pipelines | Built-in eval framework, CI/CD | Via PydanticAI integration |
| **Prompt management** | Yes (versioned prompts) | Yes (experiments + datasets) | No |
| **Framework support** | Any (OpenAI, Anthropic, LangChain, PydanticAI, etc.) | Any (via proxy or SDK) | Python-focused (Pydantic, PydanticAI, FastAPI) |
| **Strength** | Flexibility, open-source, universal | Eval-to-production loop, PM-friendly | Zero-config for Pydantic stack |
| **Weakness** | Build-your-own eval infra | Vendor lock-in | Python-only, no prompt management |

### Decision Tree

```
What's your AI stack?
├── PydanticAI (Python-only)?
│   ├── Want zero-config tracing? → Logfire
│   └── Need evals + prompt management? → Langfuse (+ Logfire for tracing)
├── Multi-framework / multi-language?
│   ├── Want open-source / self-host? → Langfuse
│   └── Want eval CI/CD on PRs? → Braintrust
└── Just starting?
    └── Langfuse (most flexible, open-source, easy to switch later)
```

### Quick Start

```python
# Langfuse — works with any framework
from langfuse import Langfuse
langfuse = Langfuse()
trace = langfuse.trace(name="my-agent-run")

# Logfire — zero-config for PydanticAI
import logfire
logfire.configure()
logfire.instrument_pydantic_ai()

# Braintrust — wrap any LLM call
from braintrust import init_logger
logger = init_logger(project="my-project")
```

> **Start with Langfuse** unless you're pure PydanticAI (Logfire) or need eval CI/CD in GitHub Actions (Braintrust). All three can coexist — Langfuse for tracing, Braintrust for evals, Logfire for Pydantic debugging.

---

## Content & Image Generation

> **For developer workflows**, not core product features.

| Tool | Use Case | Notes |
|------|----------|-------|
| **gamma.app** | Presentations, pitch decks | AI slide generation |
| **krea.ai** | Logos, visual assets | Image generation for branding |
| **Midjourney/DALL-E** | Marketing imagery | General image generation |

### When to Use

- **Demos**: gamma.app for quick pitch decks
- **Branding**: krea.ai for logo exploration
- **Documentation**: AI-generated diagrams and illustrations

---

## Workflow Integration

### Recommended Setup

```
Daily Development:
├── Claude Code (primary coding agent)
│   └── MCP servers for database, file system
├── Cursor (IDE integration)
│   └── VS Code with Copilot disabled (avoid conflicts)
└── bolt.new (prototyping)
    └── Export to local repo when ready

Feature Development:
1. Claude Code: Design + architecture decision
2. Claude Code: Initial implementation
3. Cursor: Refinement + debugging
4. Manual: Code review + testing
5. Commit

Prototyping:
1. bolt.new: Quick MVP (10-20 min)
2. Export to local
3. Claude Code: Enhance + production-ready
```

### MCP Integration (Claude Code)

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/path/to/projects"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-postgres", "postgresql://..."]
    }
  }
}
```

---

## What Works vs Hype

### Actually Works (2026)

- **Agentic coding**: Claude Code running 7+ hours autonomously on complex tasks
- **Productivity multiplier**: 30% more output (not 30% faster)
- **Code generation**: 41% of code is now AI-generated
- **Multi-agent coordination**: Specialized agents working together

### Still Hype

- "AI will replace developers" — 0% of work is fully delegable
- "Set and forget" — Active supervision still required
- "Any tool works" — Tool choice matters significantly
- "Specialized generators for everything" — General models often better

### Production Reality

| AI Excels At | AI Struggles With |
|--------------|-------------------|
| Well-defined tasks | Architectural decisions |
| Repetitive code | Organizational context |
| Easily verifiable work | Design trade-offs |
| Pattern matching | Novel problem solving |
| Documentation | Security review |

---

## Quick Reference

### For This Stack (SvelteKit + Python + TypeScript)

| Task | Tool |
|------|------|
| Complex feature | Claude Code |
| Quick fix / debug | Cursor |
| Full-stack prototype | bolt.new |
| Svelte components | Claude Code |
| React components (then adapt) | v0.dev |
| Python agents (simple) | PydanticAI |
| TypeScript agents | Mastra |
| Python agents (multi-agent) | CrewAI or Google ADK |
| Structured outputs | Instructor |
| LLM tracing/eval (general) | Langfuse |
| LLM eval CI/CD | Braintrust |
| PydanticAI tracing | Logfire |
| Presentations | gamma.app |

### Skip These

| Tool | Why |
|------|-----|
| Devin | Expensive, Claude Code is better for most tasks |
| Specialized Svelte generators | Immature, Claude Code is more reliable |
| Multiple coding assistants simultaneously | Conflicts, context confusion |

---

## AI Coding Tools Landscape

> **Freshness**: 2026-04-17 — benchmarks and market positions change fast. Verify before making purchase decisions.

### Model Quality for Coding (SWE-bench Verified, March 2026)

| Model | Score | Notes |
|-------|-------|-------|
| Claude Opus 4.6 | 80.8% | Best for deep reasoning, multi-file refactoring, vague specs |
| Gemini 3.1 Pro | 80.6% | Best price-to-performance, 1M context |
| GPT-5.2 | 80.0% | Best speed and terminal execution |
| Claude Sonnet 4.6 | 79.6% | Near-flagship at 1/5 cost — the workhorse |
| Copilot (internal) | 56.0% | Lower than flagships, but free tier strong |

Top-tier is a three-way race. Route different tasks to different models rather than picking one.

### Terminal Agents (Claude Code competitors)

| Tool | Model | Differentiator | Cost | Status |
|------|-------|---------------|------|--------|
| **Claude Code** | Opus 4.6 / Sonnet 4.6 | Hooks, skills, plugins, MCP, desktop app, routines | $20-200/mo | **Active** |
| **Codex CLI** | o4-mini (default) | Open-source (MIT), fire-and-forget, cheaper tokens | $20-100/mo | **Active** |
| **Gemini CLI** | Gemini 2.5 Pro | Free tier, 1M context, low overhead | Free-$20/mo | Disabled |
| **Copilot CLI** | Multi-model | Fleet mode, cloud delegation (`&` prefix), MCP support | $10-19/mo | Disabled |
| **Junie CLI** | Multi-model (BYOK) | JetBrains ecosystem, LLM-agnostic | Beta (free) | Watch |
| **Aider** | Any | Open-source, auto git commits, model-agnostic | BYO keys | Watch |

### AI-Native IDEs

| Tool | Differentiator | Cost | Status |
|------|---------------|------|--------|
| **Cursor** | Supermaven autocomplete (72% acceptance), Composer 2, background agents | $20-200/mo | **Active** |
| **Windsurf 2.0** (Cognition/Devin) | Native Devin integration, Agent Command Center | $15-50/mo | Watch |
| **Antigravity** (Google) | Dual Editor/Manager view, multi-agent orchestration | Free-paid | Disabled |
| **Zed** | ACP (Agent Client Protocol — "LSP for AI agents"), GPU-accelerated | Free | Watch |

### IDE Extensions

| Tool | Best For | Cost | Status |
|------|----------|------|--------|
| **GitHub Copilot** | Teams with GitHub integration, 37% market share | $10-19/mo | Disabled |
| **Gemini Code Assist** | Google Cloud / Android Studio workflows | Free-paid | Disabled |
| **Amazon Q Developer** | AWS-heavy workflows, security scans | $19/user/mo | Watch |
| **Augment Code** | Enterprise, 500K+ file context engine | $20-200/mo | Watch |
| **Sourcegraph Cody** | Large polyglot orgs, cross-repo code graph | $59/user/mo | Watch |
| **Codex IDE Extension** | Codex Cloud from inside Cursor/VS Code | Included w/ ChatGPT | Disabled |

### Autonomous Cloud Agents

| Tool | How It Works | Status |
|------|-------------|--------|
| **Codex Cloud** (OpenAI) | Sandboxed env per task in ChatGPT, writes PRs, parallel tasks | Watch |
| **Jules** (Google) | Async against GitHub repos, plans/codes/submits PRs | Watch |
| **Devin** (Cognition) | Full autonomous env with terminal, browser, tests | Watch |
| **Copilot Coding Agent** | Runs in GitHub Actions, converts issues to PRs | Watch |
| **Codex Security** (OpenAI) | AppSec agent: threat model → fuzzing → fix PRs. Web-only, research preview | Watch |
| **Claude Code Routines** | Server-side scheduled automations (cron, webhooks, API) | Active (preview) |

### Protocols & Standards

| Protocol | What It Does | Adoption |
|----------|-------------|----------|
| **MCP** (Model Context Protocol) | "USB-C for AI" — standardized tool/resource integration | 10K+ servers, all major players |
| **ACP** (Agent Client Protocol) | "LSP for AI agents" — decouples agents from editors | Zed, JetBrains |
| **AG-UI** | Agent-User Interaction Protocol — standardizes agent UIs | Early |

### Market Perception (Developer Sentiment, Q1 2026)

| Question | Answer |
|----------|--------|
| Best coding models? | Three-way race: Claude, GPT, Gemini (all ~80% SWE-bench) |
| Best IDE wrapper? | Cursor (19% most-loved, #2). Power users pair it with Claude Code |
| Google getting love? | Respect, not love. Great benchmarks + price. Tendency to over-rewrite |
| GitHub Copilot? | "Toyota Camry" — largest install, cheapest, not exciting. 9% most-loved |
| Claude Code vs Codex? | Claude = faster, interactive, more loved. Codex = cheaper, more autonomous, stricter rules |
| Average tools per dev? | 2.3 — no single tool wins everything |

---

## Autonomous & Scheduled Coding

> **Freshness**: 2026-04-17 — This space is moving fast. Claude Code Routines are still in preview.

### Platform Comparison

| Platform | Scheduled | Event Triggers | API Trigger | Runs in Cloud | Status | Min Price |
|----------|-----------|----------------|-------------|---------------|--------|-----------|
| **Claude Code Routines** | Hourly+ cron | GitHub PR/release | HTTP POST | Yes | Preview | $20/mo |
| **Cursor Automations** | Cron-style | Slack, Linear, GitHub, PagerDuty, webhooks | No | Yes | GA | $20/mo |
| **Codex Cloud** | Minute/daily/weekly/cron | GitHub `@codex` mentions | Yes (API) | Yes | GA | $20/mo |
| **Jules** | Daily/weekly (web UI) | No | Alpha (no scheduling) | Yes | GA | Free |
| **Copilot Coding Agent** | No | Manual issue-assign only | No | Yes | GA | $10/mo |
| **Devin** | Yes (configurable) | Slack, Jira, Linear, API | Yes | Yes | GA | $500/mo |

### What Each Actually Offers

**Claude Code Routines** — Three tiers of automation:
- `/loop 5m <prompt>` — session-scoped polling (7-day expiry, max 50 tasks)
- Desktop scheduled tasks — runs on your machine, no open session needed
- Cloud Routines — Anthropic's infra, fresh repo clone each run, pushes to `claude/`-prefixed branches
- Triggers: cron (hourly minimum), GitHub events (PR/release with author/label/branch filters), HTTP POST API
- Limits: ~5 runs/day on Pro, ~15 on Max. Each run draws from subscription usage.
- Create via: claude.ai/code/routines, Desktop app, or `/schedule` in CLI

**Cursor Automations** — Best event trigger ecosystem:
- Cron schedules + event triggers: Slack messages, Linear issues, GitHub PR merges, PagerDuty incidents, custom webhooks
- Agents run in isolated cloud sandboxes with memory across runs
- Create at cursor.com/automations or from marketplace templates
- No programmatic API for creating automations

**Codex Cloud** — Most flexible scheduling:
- Thread automations (preserves conversation context) or standalone
- Minute-granularity scheduling, daily, weekly, or custom cron
- API available: `gpt-5.2-codex` model, $1.75/$14 per 1M input/output tokens + container fees
- `codex cloud` CLI command for managing cloud tasks

**Jules** — Simplest, cheapest:
- Schedule daily/weekly from web UI. Edit/pause/resume.
- API is alpha — no scheduling support, sessions execute immediately
- Templates: performance optimization, security hardening, design/UX improvements
- Free. No config needed — reads AGENTS.md from your GitHub repo.

**Copilot Coding Agent** — No scheduling, but useful for issue-driven work:
- Assign an issue to "Copilot" in GitHub, it makes a PR
- Can trigger via `@copilot` in PR comments
- Third-party: Azure Boards, Jira (preview), Linear, Slack

### Appraisal: What's Worth Setting Up

**Safe to automate (verifiable, low blast radius):**

| Task | Schedule | Tool | Why |
|------|----------|------|-----|
| Dependency audit | Weekly | Claude Routine | `cargo audit` / `npm audit` / `uv pip check` — output is a report, not code changes |
| Stale branch cleanup | Weekly | Claude Routine | Delete merged branches, list orphaned ones — reversible |
| License compliance | Monthly | Claude Routine | Scan deps for license violations — report only |
| README/docs drift | Weekly | Cursor Automation | Diff code vs docs, flag discrepancies — report or draft PR |
| Test suite health | Daily | Codex Cloud | Run full test suite, report failures — no code changes |
| Backlog triage | Weekly | Jules | Simple, well-scoped GitHub issues → PRs for review |

**Automate with supervision (create PRs, don't merge):**

| Task | Schedule | Tool | Why Supervised |
|------|----------|------|---------------|
| Dependency upgrades | Weekly | Claude Routine | Breaking changes need manual testing |
| Dead code removal | Monthly | Claude Routine | False positives possible |
| API docs generation | On PR merge | Cursor Automation | Generated docs need accuracy review |
| Performance profiling | Weekly | Codex Cloud | Optimization suggestions need architectural judgment |

**Don't automate (needs human judgment):**

| Task | Why Not |
|------|---------|
| Feature development | Spec interpretation needs context |
| Architecture refactoring | Design decisions compound — bad ones are expensive |
| Security fixes | Must verify the fix doesn't introduce new vulnerabilities |
| Database migrations | Data loss risk, needs human sign-off |

### Setup Checklist

To start using Claude Code Routines:
1. Ensure GitHub is connected at claude.ai/code
2. Go to claude.ai/code/routines (or use `/schedule` in CLI)
3. Pick a repo + branch
4. Write a prompt (see `prompts/guides/prompt-tactics.md` for templates)
5. Set schedule (start with weekly, promote to daily once you trust the output)
6. Review the `claude/`-prefixed branch it creates — merge manually

To start using Cursor Automations:
1. Go to cursor.com/automations
2. Create from template or custom
3. Configure trigger (start with cron, add events later)
4. Set instructions and model
5. Review output in the automation history

### Key Insight

> **Autonomous ≠ unsupervised.** The best use of scheduled agents is "supervised autonomy" — they do the work, you review the output. Think of them as a junior engineer who runs nightly scripts and leaves you a report every morning. The report is the PR diff.

---

## Cost Considerations

| Tool | Pricing Model | Typical Cost |
|------|---------------|--------------|
| Claude Code | API usage (Claude Pro/Max) | $20-200/month (Pro $20, Max from $100) |
| Codex CLI | ChatGPT Pro/Team/Enterprise | $20-100/month |
| OpenCode | BYO keys or Zen gateway | $10/mo (Zen open models) or BYO API keys |
| Cursor | Subscription | $20/month (Pro), $60/month (Pro+), $200/month (Ultra) |
| GitHub Copilot | Subscription | $10-19/month |
| bolt.new | Credits | Free tier + $20/month |
| v0.dev | Credits | Free tier + usage |
| Gemini CLI | Free tier + Google AI Pro | Free-$20/month |

**Budget recommendation**: Claude Pro ($20) + Cursor Pro ($20) = $40/month for full AI-assisted development. Add Codex Pro ($20) for cross-model review workflows. Upgrade to Max/Pro+ when you need higher limits.

---

## Watch & Revisit

> Tools and libraries to keep an eye on. Not yet evaluated or integrated, but showing promise.

### AI Agents & Memory

| Tool | What It Does | Why Watch |
|------|--------------|-----------|
| **OpenClaw** (prev MoltBot) | Open-source self-hosted AI agent/personal assistant | Runs on Mac mini or Cloudflare Workers; integrations for chat, AI models, tools |
| **claude-supermemory** | Persistent memory for Claude Code across sessions | Context injection, automatic capture, codebase indexing |
| **claude-subconscious** | Letta agent that observes Claude Code sessions | Accumulates patterns across sessions, provides async guidance via CLAUDE.md |
| **OpenCode** | Open-source local-first AI coding agent | **Promoted to Tier 2** — see AI Coding Assistants section above. |
| **Open WebUI** | Self-hosted AI platform interface | Unified UI for any AI model (Ollama/OpenAI/Anthropic); Python extensions; RAG/voice/vision; Docker install; 328k+ community members |
| **oh-my-claudecode (OMC)** | Multi-agent orchestration plugin for Claude Code | "Oh-My-Zsh for Claude Code"; autopilot/ultrapilot/swarm modes; 32+ agents, 40+ skills; zero config, natural language commands |
| **GSD (Get Shit Done)** | Spec-driven execution framework for Claude Code | v2 is a standalone TS CLI on Pi SDK; context management, autonomous task sequencing, crash recovery; 35k+ GitHub stars |
| **Codex Security** | OpenAI AppSec agent | Threat model → fuzzing → fix PRs; web-only (codex.openai.com); research preview for Pro/Enterprise |
| **Pi** | Minimal terminal coding harness | Multi-provider (15+ providers); extensibility-first (no built-in MCP/sub-agents — build as extensions); tree-structured sessions; SDK embedding; npm/git package ecosystem; GSD v2 built on it |

**Links**:
- OpenClaw: https://github.com/openclaw/openclaw
- OpenClaw + Cloudflare: https://blog.cloudflare.com/moltworker-self-hosted-ai-agent/
- claude-supermemory: https://github.com/supermemoryai/claude-supermemory
- claude-subconscious: https://github.com/letta-ai/claude-subconscious
- OpenCode: https://github.com/opencode-ai/opencode | https://opencode.ai/
- Open WebUI: https://github.com/open-webui | https://www.openwebui.com/
- oh-my-claudecode: https://github.com/Yeachan-Heo/oh-my-claudecode
- GSD: https://github.com/gsd-build/get-shit-done | https://github.com/gsd-build/gsd-2
- Codex Security: https://developers.openai.com/codex/security
- Pi: https://pi.dev/

### Agent Protocols

| Tool | What It Does | Why Watch |
|------|--------------|-----------|
| **AG-UI** | Agent-User Interaction Protocol | Standardizes how AI agents connect to UIs; complements MCP (tools) and A2A (agent-to-agent); good for MCP Apps |

**Links**:
- AG-UI: https://github.com/ag-ui-protocol/ag-ui

### Python ML Libraries (Feature Engineering)

| Library | Use Case | Notes |
|---------|----------|-------|
| **NVTabular** | GPU-accelerated tabular preprocessing | NVIDIA-Merlin; for deep learning recommenders at scale |
| **FeatureTools** | Automated feature engineering | Deep feature synthesis on relational/time-series data |
| **Dask** | Parallel Pandas/scikit-learn | Cluster-based computations for large datasets |
| **Polars** | High-performance dataframes | Rust-based, lazy evaluation; Pandas alternative |
| **Feast** | Feature store | Ensures training/inference consistency; pairs with denormalized |
| **tsfresh** | Time series feature extraction | Hundreds of features + relevance filtering |
| **River** | Online/streaming ML | Handles unbounded data and concept drift |

**Links**:
- NVTabular: https://github.com/NVIDIA-Merlin/NVTabular
- FeatureTools: https://github.com/alteryx/featuretools
- Dask: https://www.dask.org/
- Polars: https://pola.rs/
- Feast: https://feast.dev/
- tsfresh: https://tsfresh.readthedocs.io/
- River: https://github.com/online-ml/river

### Runtimes & Tools

| Tool | What It Does | Why Watch |
|------|--------------|-----------|
| **Deno 2** | TypeScript-first runtime | Native TypeScript, built-in tooling, Node.js compatibility mode; mature alternative to Bun for TypeScript-first serverless |
| **Marimo** | Reactive Python notebooks | Git-friendly .py files instead of .ipynb; reactive execution; modern Jupyter alternative |
| **Hex** | Hosted notebook platform | Collaborative SQL + Python notebooks; great for data teams; alternative to Jupyter/Marimo for shared analysis |
| **Pulumi** | Infrastructure as Code | **Moved to services.md** — see Infrastructure as Code section. |
| **Temporal** | Durable workflow engine | Reliable distributed workflows, task queues, retries; use instead of rolling your own job queue or saga pattern |
| **Exa AI** | AI-powered web search API | Semantic search for agents; free tier available; good MCP integration for research tasks |

**Links**:
- Deno: https://deno.com/
- Marimo: https://marimo.io/
- Hex: https://hex.tech/
- Pulumi: https://www.pulumi.com/
- Temporal: https://temporal.io/
- Exa: https://exa.ai/

### Tunneling

For exposing local services (webhooks, demos, mobile testing):

| Tool | Notes |
|------|-------|
| **cloudflared** | Preferred. Free, no account needed for quick tunnels. `brew install cloudflared` then `cloudflared tunnel --url localhost:3000` |
| **ngrok** | Alternative. More features (custom domains, inspection). Free tier available. |

### Monorepo Tools

When a project outgrows a single package:

| Tool | Language | Notes |
|------|----------|-------|
| **moon** | Any (Rust-based) | Preferred. Fast, language-agnostic, smart caching, project graph. Best DX. |
| **Turborepo** | JS/TS | Vercel ecosystem. Good for pure JS/TS monorepos. Simpler than moon. |
| **Pants** | Python/Go/Java | Best for large polyglot repos. Steeper learning curve. |

> **Start with moon** unless you're JS/TS-only (Turborepo) or have a large polyglot backend (Pants).

### To Investigate

- **Ralph Wiggum AI** - AI "software engineer" for testing NPM package compatibility (mentioned in Cloudflare blog)
