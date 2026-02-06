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

### Agent SDKs

| Framework | Language | Use Case | Maturity |
|-----------|----------|----------|----------|
| **PydanticAI** | Python | Agents with tool calling, type-safe | Production-ready |
| **Google ADK** | Python | Multi-agent systems, hierarchical agents | Production-ready |
| **CrewAI** | Python | Role-based multi-agent collaboration | Production-ready |
| **AutoGen** | Python | Async multi-agent conversations | Production-ready |
| **LangGraph** | Python/TS | Graph-based workflows, complex orchestration | Production-ready |
| **LlamaIndex Agents** | Python | RAG-heavy agents, knowledge retrieval | Production-ready |
| **OpenAI Agents SDK** | Python | OpenAI-ecosystem agents, built-in tools | Production-ready |
| **Mastra** | TypeScript | Agents with tool calling, workflows | Production-ready |
| **Strands Agents** | Python | Strong observability, AWS-optimized | Production-ready |
| **Smolagents** | Python | Minimal, code-centric agents | Production-ready |

### Specialized Tools

| Tool | Language | Use Case | Notes |
|------|----------|----------|-------|
| **Instructor** | Python | Structured outputs from LLMs | Not a full agent framework, pairs with others |

### Decision Tree

```
What language?
├── Python
│   ├── Need structured output? → Instructor
│   ├── Need tool calling (simple)? → PydanticAI
│   ├── Need multi-agent (role-based)? → CrewAI or Google ADK
│   ├── Need multi-agent (async/chat)? → AutoGen
│   ├── Need multi-agent (graph-based)? → LangGraph
│   ├── Need RAG-heavy agents? → LlamaIndex Agents
│   └── Need minimal/code-centric? → Smolagents
└── TypeScript
    ├── Need agents + workflows? → Mastra
    └── Need multi-agent? → LangGraph
```

### Framework Comparison

| Feature | PydanticAI | Google ADK | CrewAI | AutoGen | LangGraph |
|---------|------------|------------|--------|---------|-----------|
| Type safety | ★★★ | ★★☆ | ★☆☆ | ★☆☆ | ★★☆ |
| Multi-agent | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| Learning curve | Low | Medium | Low | Medium | High |
| Provider lock-in | None | None (LiteLLM) | None | None | None |
| Built-in eval | No | Yes | No | No | Yes |
| MCP support | Yes | Yes | No | No | Yes |

### Quick Recommendations

- **Simple agents with tools**: PydanticAI (best DX, type-safe)
- **Multi-agent with hierarchy**: Google ADK (enterprise-ready, good tooling)
- **Multi-agent with roles**: CrewAI (easy setup, clear mental model)
- **Async conversations**: AutoGen (event-driven, real-time)
- **RAG/knowledge-heavy agents**: LlamaIndex Agents (best retrieval integration)
- **Complex workflows**: LangGraph (most flexible, steepest learning curve)

> **Note**: Google ADK is optimized for Google Cloud but works anywhere. It supports Anthropic, OpenAI, Meta, Mistral and more via LiteLLM integration, avoiding vendor lock-in. For most projects, PydanticAI + a TypeScript frontend is cleanest. Use CrewAI or ADK when you need multi-agent coordination.

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
// ~/.config/claude/config.json
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
| Python agents (multi-agent) | CrewAI or Google ADK |
| Structured outputs | Instructor |
| Presentations | gamma.app |

### Skip These

| Tool | Why |
|------|-----|
| Devin | Expensive, Claude Code is better for most tasks |
| Specialized Svelte generators | Immature, Claude Code is more reliable |
| LangChain (directly) | Bloated, use PydanticAI or specialized frameworks instead |
| Multiple coding assistants simultaneously | Conflicts, context confusion |

---

## Cost Considerations

| Tool | Pricing Model | Typical Cost |
|------|---------------|--------------|
| Claude Code | API usage | $20-100/month depending on usage |
| Cursor | Subscription | $20/month |
| bolt.new | Credits | Free tier + $20/month |
| v0.dev | Credits | Free tier + usage |
| GitHub Copilot | Subscription | $10-19/month |

**Budget recommendation**: Claude Code + Cursor = ~$40-50/month for full AI-assisted development.

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

### To Investigate

- **Ralph Wiggum AI** - AI "software engineer" for testing NPM package compatibility (mentioned in Cloudflare blog)
