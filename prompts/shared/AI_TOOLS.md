# AI Development Tools

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
| **GitHub Copilot** | Enterprise teams with GitHub integration |
| **Windsurf (Codeium)** | Budget-conscious, free tier available |
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
| Presentations | gamma.app |

### Skip These

| Tool | Why |
|------|-----|
| Devin | Expensive, Claude Code is better for most tasks |
| Specialized Svelte generators | Immature, Claude Code is more reliable |
| Multiple coding assistants simultaneously | Conflicts, context confusion |

---

## Cost Considerations

| Tool | Pricing Model | Typical Cost |
|------|---------------|--------------|
| Claude Code | API usage (Claude Pro/Max) | $20-100/month (Pro $20, Max from $100) |
| Cursor | Subscription | $20/month (Pro), $60/month (Pro+), $200/month (Ultra) |
| bolt.new | Credits | Free tier + $20/month |
| v0.dev | Credits | Free tier + usage |
| GitHub Copilot | Subscription | $10-19/month |

**Budget recommendation**: Claude Pro ($20) + Cursor Pro ($20) = $40/month for full AI-assisted development. Upgrade to Max/Pro+ when you need higher limits.

---

## Watch & Revisit

> Tools and libraries to keep an eye on. Not yet evaluated or integrated, but showing promise.

### AI Agents & Memory

| Tool | What It Does | Why Watch |
|------|--------------|-----------|
| **OpenClaw** (prev MoltBot) | Open-source self-hosted AI agent/personal assistant | Runs on Mac mini or Cloudflare Workers; integrations for chat, AI models, tools |
| **claude-supermemory** | Persistent memory for Claude Code across sessions | Context injection, automatic capture, codebase indexing |
| **claude-subconscious** | Letta agent that observes Claude Code sessions | Accumulates patterns across sessions, provides async guidance via CLAUDE.md |
| **OpenCode** | Open-source local-first AI coding agent | Go-based autonomous pair programmer; supports Claude/GPT/Gemini/Ollama; terminal/desktop/VS Code; privacy-first (code stays local); 95k+ stars |
| **Open WebUI** | Self-hosted AI platform interface | Unified UI for any AI model (Ollama/OpenAI/Anthropic); Python extensions; RAG/voice/vision; Docker install; 328k+ community members |
| **oh-my-claudecode** | Multi-agent orchestration plugin for Claude Code | "Oh-My-Zsh for Claude Code"; autopilot/ultrapilot/swarm modes; 32+ agents, 40+ skills; zero config, natural language commands |

**Links**:
- OpenClaw: https://github.com/openclaw/openclaw
- OpenClaw + Cloudflare: https://blog.cloudflare.com/moltworker-self-hosted-ai-agent/
- claude-supermemory: https://github.com/supermemoryai/claude-supermemory
- claude-subconscious: https://github.com/letta-ai/claude-subconscious
- OpenCode: https://github.com/opencode-ai/opencode | https://opencode.ai/
- Open WebUI: https://github.com/open-webui | https://www.openwebui.com/
- oh-my-claudecode: https://github.com/Yeachan-Heo/oh-my-claudecode

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
| **Pulumi** | Infrastructure as Code | TypeScript/Python/Go for cloud infra; more flexible than Terraform; consider for multi-cloud projects |
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
