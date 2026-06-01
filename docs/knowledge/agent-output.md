# Working Files & Agent Artifacts

## Directory: `.agents/`

Working files, plans, research, and decisions go in `.agents/` at the project root. This keeps the main codebase clean while preserving useful context. The `.agents/` convention works across Claude Code, Cursor, Gemini, ChatGPT, and other AI tools.

> **See also**: `PROJECT_MEMORY.md` for the full two-layer decision organization system.

### Structure

```
.agents/
├── decisions/                # Architecture Decision Records (versioned)
│   ├── 0001-database-choice.md
│   ├── 0002-api-design.md
│   ├── _index.md             # Decision index (maintained)
│   └── CHANGELOG.md          # Timeline of decisions with context
├── plans/                    # Implementation plans and designs
│   ├── YYYY-MM-DD-feature-name.md
│   └── ...
├── research/                 # Investigation and analysis notes
│   ├── YYYY-MM-DD-topic.md
│   └── ...
├── prompts/                  # Key prompts that led to decisions
│   ├── feature-auth.md
│   └── ...
├── sessions/                 # Conversation logs
│   └── ...
└── README.md                 # Index of contents
```

### Rules

1. **Keep the main tree clean** — Working files go in `.agents/`, not scattered around
2. **Date-prefix files** — Use `YYYY-MM-DD-description.md` for chronological sorting
3. **Clean up when done** — Delete scratch files after they're incorporated or abandoned
4. **Version plans** — Create new version files rather than editing approved plans
5. **Include attribution** — Note who contributed what for context
6. **Decisions are versioned** — `.agents/decisions/` is committed to git; everything else is gitignored

### Attribution Tags

Attribution provides context for future readers (human or AI):

| Tag | Meaning | Context |
|-----|---------|---------|
| 👤 HUMAN | Human made this call | Loop them in before changing |
| 🤖 AI-SUGGESTED | AI proposed | Feel free to revisit |
| 🤖→👤 AI-REFINED | AI explored, human decided | Check the reasoning |
| ⚠️ ASSUMED | Nobody explicitly decided | Validate this |

**Note**: Attribution isn't about creating untouchable rules—it's about knowing who has context.

### What Goes Where

| Content Type | Location | Persistence |
|-------------|----------|-------------|
| Implementation plan | `.agents/plans/` | Gitignored (or version if useful) |
| API research | `.agents/research/` | Gitignored (or version if useful) |
| Key prompts | `.agents/prompts/` | Gitignored (or version if useful) |
| Code experiments | `.agents/` | Delete when done |
| Debug notes | `.agents/` | Delete when done |
| Conversation logs | `.agents/sessions/` | Gitignored |
| **Architecture decisions** | `.agents/decisions/` | **Versioned** (committed to git) |
| **Decision timeline** | `.agents/decisions/CHANGELOG.md` | **Versioned** (committed to git) |

### .gitignore Entry

```gitignore
# Working files (ephemeral by default)
.agents/

# Keep decisions versioned
!.agents/decisions/
```

### What Gets Auto-Discovered

Claude Code automatically loads `AGENTS.md` at project root. It does NOT auto-discover `.agents/`. Reference it in `AGENTS.md` if you want AI to know about decisions and working files:

```markdown
## Project Organization
- Working files: `.agents/`
- Decision history: `.agents/decisions/`
```

### Plan File Format

```markdown
# Plan: {Feature Name}

**Created**: YYYY-MM-DD
**Author**: Claude 🤖 | @username 👤 | Both 🤖→👤
**Status**: Draft | Approved | Implemented | Superseded

## Summary
One-paragraph description of what this plan accomplishes.

## Attribution
- Research: 🤖 AI-SUGGESTED
- Approach: 🤖→👤 AI-REFINED (human approved)
- Constraints: 👤 HUMAN (from AGENTS.md project context)

## Context
Why are we doing this? What problem does it solve?

## Approach
How will we implement this?

## Tasks
- [ ] Task 1
- [ ] Task 2

## Open Questions
- Question that needs human input ⚠️ ASSUMED

## Related
- ADR: .agents/decisions/000X-related.md
- Previous plan: .agents/plans/YYYY-MM-DD-previous.md
```

### Research File Format

```markdown
# Research: {Topic}

**Created**: YYYY-MM-DD
**Author**: Claude 🤖

## Question
What are we trying to learn?

## Findings

### Option A: {Name}
**Pros**: ...
**Cons**: ...

### Option B: {Name}
**Pros**: ...
**Cons**: ...

## Recommendation
🤖 AI-SUGGESTED: Based on [criteria], recommend Option A.

⚠️ ASSUMED: This assumes [assumption]. Validate with human.

## Sources
- [Link 1]
- [Link 2]
```

### Auto-Index

If you version `.agents/`, maintain a README:

```markdown
# Working Files

Last updated: YYYY-MM-DD

## Active Plans
- [Feature Name](plans/YYYY-MM-DD-feature-name.md) - 🤖→👤 Brief description

## Research
- [Topic](research/YYYY-MM-DD-topic.md) - 🤖 Brief description

## Key Prompts
- [Auth exploration](prompts/auth-exploration.md) - Led to ADR-0005

## Archived
- [Old Plan](plans/YYYY-MM-DD-old.md) - Superseded by [New Plan]
```

### Prompt Archive Format

When a significant decision emerges from exploration, archive the key prompts:

```markdown
# Prompts: {Decision Topic}

**Related ADR**: ADR-000X
**Date**: YYYY-MM-DD

## Initial Exploration
> "Compare Auth0 vs NextAuth vs Better Auth for our use case.
> Requirements: OAuth, magic links, 2FA, self-hosted preferred."

## Follow-up
> "Given Better Auth, design the migration path from our current
> custom auth. Zero downtime required."

## Human Input
@alice: "Also need to support HIPAA compliance for healthcare clients."

## Outcome
See ADR-000X for the decision.
```

---

## Summary

| Directory | Purpose | Versioned | Auto-Discovered |
|-----------|---------|-----------|-----------------|
| `AGENTS.md` | Project instructions + context | Yes | Yes (Claude, Cursor, etc.) |
| `.agents/decisions/` | Architecture decisions & ADRs | Yes | No (reference in AGENTS.md) |
| `.agents/` (other) | Working files | No (gitignored) | No |
