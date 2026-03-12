# Project Memory & Decision Organization

**Philosophy**: Maintain a clear, layered system that distinguishes current state from working context, with attribution for context—not to create rules that can never be questioned.

> **Key Insight**: The best project memory files are hand-curated, ~300-500 lines max.
> Auto-generated documentation becomes "balls of mud." Quality over quantity.

---

## The Two-Layer System

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: CURRENT STATE (Living, curated)                           │
│ "What is true right now?"                                          │
│ └── AGENTS.md (project instructions + project context)             │
│     ├── How we build (conventions, stack, process)                  │
│     └── Project Context section (what we're building, why)          │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: WORKING CONTEXT (Ephemeral + decisions)                   │
│ "What am I working on? Why did we decide this?"                    │
│ ├── .agents/plans/* (implementation plans)                         │
│ ├── .agents/research/* (investigation notes)                       │
│ ├── .agents/sessions/* (conversation logs)                         │
│ ├── .agents/prompts/* (key prompts that led to decisions)          │
│ └── .agents/decisions/* (ADRs — versioned, committed to git)       │
└─────────────────────────────────────────────────────────────────────┘
```

### What's Versioned

- `AGENTS.md` — always committed. Source of truth for current state.
- `.agents/decisions/` — committed to git via `!.agents/decisions/` in `.gitignore`. This is the only versioned subset of `.agents/`.
- Everything else in `.agents/` — gitignored. Ephemeral working files.

### Naming

`AGENTS.md` is the cross-platform convention that works with Claude Code, Cursor, Gemini, ChatGPT, and others. Think of it as **project instructions for everyone**—humans and AI alike. It now includes a "Project Context" section covering what you're building and why (previously a separate `ABSTRACT.md` file).

---

## Recommended Directory Structure

```
your-project/
│
├── AGENTS.md                      # Layer 1: Project instructions + context
│
├── .agents/                       # Layer 2: Working memory + decisions
│   ├── decisions/                 # Architecture Decision Records (versioned)
│   │   ├── 0001-database-choice.md
│   │   ├── 0002-api-design.md
│   │   ├── 0003-supersedes-0002.md
│   │   ├── _index.md              # Decision index (maintained)
│   │   └── CHANGELOG.md           # Timeline of decisions with context
│   │
│   ├── plans/                     # Implementation plans (date-prefixed)
│   ├── research/                  # Investigation notes
│   ├── prompts/                   # Key prompts that led to decisions
│   └── sessions/                  # Conversation logs
│
└── .gitignore
```

### .gitignore Setup

```gitignore
# .gitignore

# Working memory (ephemeral by default)
.agents/

# Keep decisions versioned
!.agents/decisions/
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
| `.agents/decisions/*.md` | Append-only | Don't edit, supersede instead |
| `.agents/decisions/CHANGELOG.md` | Append-only | Add entries, never remove |
| `.agents/*` (other) | Ephemeral | Delete when done |

**The rule**: Layer 1 is edited. Decisions are appended. Working files are deleted.

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
ls .agents/decisions/ | grep -i "auth\|api"

# 3. Create a plan
# Create .agents/plans/2026-02-01-feature-x.md

# 4. If architectural decision needed, draft ADR
# Create .agents/decisions/0006-feature-x-approach.md (status: proposed)

# 5. Review and approve
# Change status to "accepted", add attribution
```

### Resolving Confusion About Current State

```bash
# If confused about what's current:
# 1. AGENTS.md is the source of truth for current state
# 2. .agents/decisions/CHANGELOG.md shows the evolution
# 3. ADRs in .agents/decisions/ explain the "why" behind each decision
```

### Onboarding (Human or AI)

```markdown
## Read in Order
1. AGENTS.md (what we're building + how we build it)
2. .agents/decisions/_index.md (key decisions)
3. .agents/decisions/CHANGELOG.md (recent changes)
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
| Why did we choose this? | `.agents/decisions/XXXX-*.md` |
| What changed recently? | `.agents/decisions/CHANGELOG.md` |
| What are we working on now? | `.agents/plans/` |
| Who made this decision? | Check attribution tags |
| Can I change this? | Yes—but loop in people with context first |
