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

| Framework | Language | Use Case | Maturity |
|-----------|----------|----------|----------|
| **PydanticAI** | Python | Agents with tool calling | Production-ready |
| **Instructor** | Python | Structured outputs from LLMs | Production-ready |
| **Mastra** | TypeScript | Agents with tool calling, workflows | Production-ready |
| **LangGraph** | Python/TS | Complex multi-agent orchestration | Production-ready, heavy |

### Decision Tree

```
What language?
├── Python
│   ├── Need structured output? → Instructor
│   ├── Need tool calling? → PydanticAI
│   └── Need multi-agent? → LangGraph
└── TypeScript
    ├── Need agents + workflows? → Mastra
    └── Need multi-agent? → LangGraph
```

> **Note**: Mastra is useful when you want agent capabilities in TypeScript without a separate Python backend. For most projects, PydanticAI + a TypeScript frontend is cleaner.

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
| Python agents | PydanticAI |
| Structured outputs | Instructor |
| Presentations | gamma.app |

### Skip These

| Tool | Why |
|------|-----|
| Devin | Expensive, Claude Code is better for most tasks |
| Specialized Svelte generators | Immature, Claude Code is more reliable |
| LangChain (directly) | Bloated, use PydanticAI + Instructor instead |
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
