# Project Memory & Decision Organization

**Philosophy**: Maintain a clear, layered system that distinguishes current state from historical evolution, and human decisions from AI suggestions.

> **Key Insight**: The best project memory files are hand-curated, ~300-500 lines max.
> Auto-generated documentation becomes "balls of mud." Quality over quantity.

---

## The Three-Layer System

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: CURRENT STATE (Living, curated)                           │
│ "What is true right now?"                                          │
│ ├── AGENTS.md / CLAUDE.md (300-500 lines, updated weekly)         │
│ └── PROJECT_BRIEF.md (project-specific context)                    │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: DECISION HISTORY (Immutable, append-only)                 │
│ "Why did we decide this? What changed?"                            │
│ ├── decisions/adr/*.md (Architecture Decision Records)             │
│ └── decisions/CHANGELOG.md (timeline with context)                 │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: SESSION CONTEXT (Ephemeral, personal)                     │
│ "What am I working on right now?"                                  │
│ ├── .agents/scratch/* (temporary work files)                       │
│ └── .agents/sessions/* (conversation logs, gitignored)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Directory Structure

```
your-project/
│
├── AGENTS.md                      # Layer 1: Current state (300-500 lines)
├── PROJECT_BRIEF.md               # Layer 1: Project-specific context
│
├── decisions/                     # Layer 2: Decision history
│   ├── adr/                       # Architecture Decision Records
│   │   ├── 0001-database-choice.md
│   │   ├── 0002-api-design.md
│   │   ├── 0003-supersedes-0002.md
│   │   └── _index.md              # Decision index (maintained)
│   │
│   ├── CHANGELOG.md               # Timeline of decisions with context
│   └── README.md                  # How decisions are made here
│
├── .agents/                       # Layer 3: Session/working memory
│   ├── plans/                     # Implementation plans (date-prefixed)
│   ├── research/                  # Investigation notes
│   ├── scratch/                   # Temporary work files
│   ├── sessions/                  # Conversation logs (gitignored)
│   └── prompts/                   # Key prompts that led to decisions
│
└── .gitignore                     # Ignore .agents/sessions/, *.local.md
```

---

## Attribution: Human vs AI Decisions

### The Problem

Without attribution, you lose track of:
- Which decisions were deliberate human choices (durable)
- Which decisions were AI suggestions (inspectable, challengeable)
- The reasoning chain that led to the current state

### The Solution: Decision Attribution Tags

Use these tags consistently in ADRs, CHANGELOG, and commit messages:

```markdown
## Attribution Tags

👤 HUMAN       - Explicit human decision, treat as durable
🤖 AI-SUGGESTED - AI proposed this, human approved
🤖→👤 AI-REFINED  - AI explored options, human made final call
⚠️ ASSUMED     - Implicit assumption, needs validation
```

### Example ADR with Attribution

```markdown
# ADR-0005: Authentication Strategy

**Status**: Accepted
**Date**: 2026-02-01
**Author**: @evan 👤
**AI Involvement**: Claude Code 🤖→👤

## Attribution
- Options analysis: 🤖 AI-SUGGESTED (Claude explored 4 options)
- Security requirements: 👤 HUMAN (@evan specified HIPAA needs)
- Final decision: 👤 HUMAN (team chose Better Auth)
- Implementation plan: 🤖→👤 AI-REFINED (Claude drafted, @evan approved)

## Context
[...]

## Decision
We will use Better Auth for authentication because [...]

## Consequences
[...]

## Supersedes
- ADR-0002: Original "use Lucia" decision
- Reason: Better Auth has more built-in features we need
```

---

## The Linear vs Curated Debate

### Option A: Pure Linear History
**Pattern**: Append-only, never edit old decisions
**Pros**: Complete audit trail, nothing lost
**Cons**: Hard to find current state, overwhelming for newcomers

### Option B: Curated Current State
**Pattern**: Edit AGENTS.md to reflect current truth, delete outdated content
**Pros**: Always accurate, easy onboarding
**Cons**: Lose decision history, can't see evolution

### Option C: Hybrid (Recommended)

**Keep both, with clear separation:**

| Document | Style | Update Pattern |
|----------|-------|----------------|
| `AGENTS.md` | Curated | Edit in place, keep current |
| `PROJECT_BRIEF.md` | Curated | Edit in place, keep current |
| `decisions/adr/*.md` | Immutable | Never edit, only supersede |
| `decisions/CHANGELOG.md` | Append-only | Add entries, never remove |
| `.agents/scratch/*` | Ephemeral | Delete when done |

**The rule**: Layer 1 is edited. Layer 2 is appended. Layer 3 is deleted.

---

## Handling Decision Evolution

When a decision changes:

### 1. Don't Edit the Original ADR

```markdown
# ❌ Wrong: Editing ADR-0002 to change the decision
# ✅ Right: Create ADR-0005 that supersedes ADR-0002
```

### 2. Create a Superseding ADR

```markdown
# ADR-0005: Switch from Lucia to Better Auth

**Supersedes**: ADR-0002

## Why the Change
- Original decision (ADR-0002) assumed simpler auth needs
- New requirements emerged: OAuth, magic links, 2FA
- Better Auth provides these out of box

## Decision Evolution
1. ADR-0002 (2025-09): Chose Lucia for lightweight auth
2. ADR-0005 (2026-02): Switch to Better Auth for features 👤 HUMAN

## Migration Plan
[...]
```

### 3. Update CHANGELOG.md

```markdown
# Decision Changelog

## 2026-02-01
- **ADR-0005**: Switch from Lucia to Better Auth 👤 HUMAN
  - Supersedes ADR-0002
  - Reason: Need OAuth, magic links, 2FA out of box
  - Migration: 2 weeks, no user disruption

## 2025-09-15
- **ADR-0002**: Use Lucia for authentication 👤 HUMAN
  - Simple auth needs at the time
  - [Now superseded by ADR-0005]
```

### 4. Update AGENTS.md to Current State

```markdown
## Authentication
- **Current**: Better Auth (see ADR-0005)
- **Previous**: Lucia (superseded, see ADR-0002)
```

---

## AI Challenge Protocol

When AI encounters a decision marked `🤖 AI-SUGGESTED` or `⚠️ ASSUMED`:

```markdown
## AI Behavior for Decision Types

### 👤 HUMAN Decisions
- Treat as durable constraints
- Do not challenge unless explicitly asked
- Ask before proposing alternatives

### 🤖 AI-SUGGESTED Decisions
- Can propose alternatives if context has changed
- Frame as: "This was AI-suggested. Given [new context], consider..."
- Seek human approval for changes

### ⚠️ ASSUMED Decisions
- Actively flag for review when relevant
- "This appears to be an assumption. Should we validate?"
- Encourage human confirmation
```

---

## Practical Workflows

### Starting a New Feature

```bash
# 1. Check current state
cat AGENTS.md | grep -A5 "## Architecture"

# 2. Check relevant decisions
ls decisions/adr/ | grep -i "auth\|api"

# 3. Create a plan
# AI creates .agents/plans/2026-02-01-feature-x.md

# 4. If architectural decision needed, draft ADR
# AI creates decisions/adr/0006-feature-x-approach.md (status: proposed)

# 5. Human reviews and approves
# Change status to "accepted", add 👤 tag
```

### Resolving Confusion About Current State

```bash
# If confused about what's current:
# 1. AGENTS.md is the source of truth for current state
# 2. decisions/CHANGELOG.md shows the evolution
# 3. ADRs explain the "why" behind each decision
```

### Onboarding a New Developer (or AI)

```markdown
## Read in Order
1. PROJECT_BRIEF.md (what we're building)
2. AGENTS.md (how we build it)
3. decisions/_index.md (key decisions)
4. decisions/CHANGELOG.md (recent changes)
```

---

## CHANGELOG.md Format

```markdown
# Decision Changelog

> Append-only log of significant decisions and changes.
> For full context, see the linked ADR.

## 2026-02

### 2026-02-01: Authentication Overhaul
- **ADR-0005**: Switch from Lucia to Better Auth 👤 HUMAN (@evan)
- **Supersedes**: ADR-0002
- **Context**: Need OAuth, magic links, 2FA
- **AI Involvement**: Claude explored options 🤖, human decided 👤

### 2026-02-01: Add PydanticAI for Agents
- **ADR-0006**: Use PydanticAI over LangChain 🤖→👤
- **Context**: Building AI features, needed agent framework
- **AI Involvement**: Claude recommended, team approved

## 2026-01

### 2026-01-15: Database Choice
- **ADR-0001**: Use PostgreSQL with Supabase 👤 HUMAN (@evan)
- **Context**: Need managed Postgres with auth/storage extras
- **AI Involvement**: None (human decision from start)

---

## How to Read This Log

- 👤 HUMAN: Explicit human decision, durable
- 🤖 AI-SUGGESTED: AI proposed, human approved
- 🤖→👤 AI-REFINED: AI explored, human decided
- ⚠️ ASSUMED: Needs validation
```

---

## ADR Template (MADR-based)

```markdown
# ADR-{NUMBER}: {TITLE}

**Status**: Proposed | Accepted | Superseded | Deprecated
**Date**: YYYY-MM-DD
**Author**: @username 👤 | Claude 🤖 | Both 🤖→👤
**Supersedes**: ADR-{NUMBER} (if applicable)
**Superseded by**: ADR-{NUMBER} (if applicable)

## Attribution
- Research: 👤 | 🤖 | 🤖→👤
- Options analysis: 👤 | 🤖 | 🤖→👤
- Decision: 👤 | 🤖 | 🤖→👤
- Implementation plan: 👤 | 🤖 | 🤖→👤

## Context

What is the issue that we're seeing that is motivating this decision?

## Decision Drivers

- Driver 1 (e.g., security requirement) 👤
- Driver 2 (e.g., performance need) 🤖
- Driver 3 (e.g., team preference) 👤

## Considered Options

1. **Option A** - [description]
2. **Option B** - [description]
3. **Option C** - [description]

## Decision Outcome

Chosen option: **Option B** because [justification]

### Consequences

**Good:**
- [positive consequence]

**Bad:**
- [negative consequence, trade-off accepted]

## Links

- Related ADRs: ADR-{NUMBER}
- Discussion: [link to PR/issue]
- Prompts: `.agents/prompts/{feature}-exploration.md`
```

---

## Quick Reference

| Question | Where to Look |
|----------|---------------|
| What's the current approach? | `AGENTS.md` |
| Why did we choose this? | `decisions/adr/XXXX-*.md` |
| What changed recently? | `decisions/CHANGELOG.md` |
| What are we working on now? | `.agents/plans/` |
| Was this a human or AI decision? | Check attribution tags |
| Can I change this? | 👤 = ask first, 🤖 = propose alternative |
