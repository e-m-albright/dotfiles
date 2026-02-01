# Project Memory & Decision Organization

**Philosophy**: Maintain a clear, layered system that distinguishes current state from historical evolution, with attribution for context—not to create rules that can never be questioned.

> **Key Insight**: The best project memory files are hand-curated, ~300-500 lines max.
> Auto-generated documentation becomes "balls of mud." Quality over quantity.

---

## The Three-Layer System

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: CURRENT STATE (Living, curated)                           │
│ "What is true right now?"                                          │
│ ├── AGENTS.md (300-500 lines, project instructions for everyone)   │
│ └── PROJECT_BRIEF.md (what we're building, context)                │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: DECISION HISTORY (Append-only, evolvable)                 │
│ "Why did we decide this? How has thinking evolved?"                │
│ ├── .architecture/adr/*.md (Architecture Decision Records)            │
│ └── .architecture/CHANGELOG.md (timeline with context)                │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: WORKING CONTEXT (Ephemeral, gitignored)                   │
│ "What am I working on right now?"                                  │
│ ├── .agents/plans/* (implementation plans)                         │
│ ├── .agents/research/* (investigation notes)                       │
│ └── .agents/sessions/* (conversation logs)                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Naming

`AGENTS.md` is the cross-platform convention that works with Claude Code, Cursor, Gemini, ChatGPT, and others. Think of it as **project instructions for everyone**—humans and AI alike.

---

## Recommended Directory Structure

```
your-project/
│
├── AGENTS.md                      # Layer 1: Project instructions (for humans + AI)
├── PROJECT_BRIEF.md               # Layer 1: What we're building
│
├── .architecture/                    # Layer 2: Decision history (versioned)
│   ├── adr/                       # Architecture Decision Records
│   │   ├── 0001-database-choice.md
│   │   ├── 0002-api-design.md
│   │   ├── 0003-supersedes-0002.md
│   │   └── _index.md              # Decision index (maintained)
│   │
│   ├── CHANGELOG.md               # Timeline of decisions with context
│   └── README.md                  # How decisions are made here
│
├── .agents/                       # Layer 3: Working memory (gitignored)
│   ├── plans/                     # Implementation plans (date-prefixed)
│   ├── research/                  # Investigation notes
│   ├── prompts/                   # Key prompts that led to decisions
│   └── sessions/                  # Conversation logs
│
└── .gitignore
```

### What Gets Versioned

```gitignore
# .gitignore

# Working memory (ephemeral)
.agents/

# Keep these versioned:
# .architecture/        (decision history)
# AGENTS.md          (project instructions)
# PROJECT_BRIEF.md   (project context)
```

---

## Attribution: Understanding Decision Origins

### Why Track Attribution?

Attribution isn't about creating untouchable rules—it's about **context**:
- Understanding the reasoning behind decisions
- Knowing when to seek input before changing something
- Recognizing assumptions that may need validation

**Everything is challengeable.** Attribution just helps you know who to involve in the conversation.

### Attribution Tags

Use these to provide context, not to create hierarchy:

```markdown
## Attribution Tags

👤 HUMAN       - Human made this call (involve them before changing)
🤖 AI-SUGGESTED - AI proposed, human approved (feel free to revisit)
🤖→👤 AI-REFINED  - AI explored, human decided (check reasoning in ADR)
⚠️ ASSUMED     - Implicit assumption (actively validate)
```

### How Attribution Affects Workflow

| Tag | What It Means | Before Changing |
|-----|---------------|-----------------|
| 👤 HUMAN | Someone thought carefully about this | Loop them in, understand context |
| 🤖 AI-SUGGESTED | AI's best guess at the time | Feel free to propose alternatives |
| 🤖→👤 AI-REFINED | Collaborative decision | Review the ADR reasoning |
| ⚠️ ASSUMED | Nobody explicitly decided | Validate, then decide properly |

**Note**: "Involve them" doesn't mean "get permission"—it means "benefit from their context before changing direction."

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
| `.architecture/adr/*.md` | Append-only | Don't edit, supersede instead |
| `.architecture/CHANGELOG.md` | Append-only | Add entries, never remove |
| `.agents/*` | Ephemeral | Delete when done |

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

## Working With Decisions

### For Everyone (Human or AI)

All decisions can be revisited. Attribution helps you work effectively:

```markdown
## When Working With Existing Decisions

### 👤 HUMAN Decisions
- Understand the context before proposing changes
- The person who made it likely has context you don't
- Propose alternatives, don't just override

### 🤖 AI-SUGGESTED Decisions
- These were best guesses—feel free to improve
- Context may have changed since the suggestion
- No need for ceremony to revisit these

### ⚠️ ASSUMED Decisions
- These need attention—nobody explicitly decided
- Great opportunity to make a real decision
- Convert to 👤 or 🤖→👤 once validated
```

### Healthy Decision Culture

- **No decision is sacred**—but decisions have context
- **Challenge respectfully**—understand before proposing alternatives
- **Document changes**—future you will thank present you
- **Assumptions decay**—revisit ⚠️ items periodically

---

## Practical Workflows

### Starting a New Feature

```bash
# 1. Check current state
cat AGENTS.md | grep -A5 "## Architecture"

# 2. Check relevant decisions
ls .architecture/adr/ | grep -i "auth\|api"

# 3. Create a plan
# Create .agents/plans/2026-02-01-feature-x.md

# 4. If architectural decision needed, draft ADR
# Create .architecture/adr/0006-feature-x-approach.md (status: proposed)

# 5. Review and approve
# Change status to "accepted", add attribution
```

### Resolving Confusion About Current State

```bash
# If confused about what's current:
# 1. AGENTS.md is the source of truth for current state
# 2. .architecture/CHANGELOG.md shows the evolution
# 3. ADRs explain the "why" behind each decision
```

### Onboarding (Human or AI)

```markdown
## Read in Order
1. PROJECT_BRIEF.md (what we're building)
2. AGENTS.md (how we build it)
3. .architecture/_index.md (key decisions)
4. .architecture/CHANGELOG.md (recent changes)
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

- 👤 HUMAN: Human made this call
- 🤖 AI-SUGGESTED: AI proposed, human approved
- 🤖→👤 AI-REFINED: Collaborative decision
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
| Why did we choose this? | `.architecture/adr/XXXX-*.md` |
| What changed recently? | `.architecture/CHANGELOG.md` |
| What are we working on now? | `.agents/plans/` |
| Who made this decision? | Check attribution tags |
| Can I change this? | Yes—but loop in people with context first |
