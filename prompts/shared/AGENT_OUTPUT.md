# Agent Output Organization

## Directory: `.agents/`

All agent-generated artifacts MUST be placed in the `.agents/` directory at the project root. This keeps the main codebase clean and provides a clear audit trail of agent work.

> **See also**: `PROJECT_MEMORY.md` for the full three-layer decision organization system.

### Structure

```
.agents/
├── plans/                    # Implementation plans and designs
│   ├── YYYY-MM-DD-feature-name.md
│   └── ...
├── research/                 # Investigation and analysis notes
│   ├── YYYY-MM-DD-topic.md
│   └── ...
├── scratch/                  # Temporary work files, experiments
│   └── ...
├── sessions/                 # Conversation logs (gitignored)
│   └── ...
├── prompts/                  # Key prompts that led to decisions
│   ├── feature-auth.md
│   └── ...
└── README.md                 # Auto-generated index of contents
```

### Rules

1. **Never pollute the main tree** — Don't create random markdown files in `src/`, `docs/`, or project root
2. **Date-prefix files** — Use `YYYY-MM-DD-description.md` for chronological sorting
3. **Clean up scratch** — Delete scratch files after they're no longer needed
4. **Plans are versioned** — Create new version files rather than editing approved plans
5. **Attribution required** — Mark AI-generated content with attribution tags

### Attribution Tags

Use these tags in all agent-generated content:

| Tag | Meaning | Usage |
|-----|---------|-------|
| 👤 HUMAN | Human-authored | Durable decisions, don't challenge |
| 🤖 AI-SUGGESTED | AI proposed | Inspectable, can revisit with new context |
| 🤖→👤 AI-REFINED | AI explored, human decided | Hybrid attribution |
| ⚠️ ASSUMED | Implicit assumption | Flag for human validation |

### What Goes Where

| Content Type | Location | Persistence |
|-------------|----------|-------------|
| Implementation plan | `.agents/plans/` | Versioned |
| API research | `.agents/research/` | Versioned |
| Code experiments | `.agents/scratch/` | Delete when done |
| Debug notes | `.agents/scratch/` | Delete when done |
| Conversation logs | `.agents/sessions/` | Gitignored |
| Key prompts | `.agents/prompts/` | Versioned (optional) |
| **Architecture decisions** | `decisions/adr/` | Permanent (Layer 2) |
| **Decision timeline** | `decisions/CHANGELOG.md` | Permanent (Layer 2) |

### Where Architecture Decisions Go

**Important**: Architecture Decision Records (ADRs) do NOT go in `.agents/`. They go in `decisions/adr/` at the project root because they are Layer 2 (permanent history), not Layer 3 (ephemeral session data).

```
# Wrong
.agents/plans/2024-01-15-adr-database.md

# Right
decisions/adr/0001-database-choice.md
```

### .gitignore Entry

Add to your `.gitignore`:

```gitignore
# Agent session artifacts (ephemeral)
.agents/scratch/
.agents/sessions/

# Keep these versioned:
# .agents/plans/
# .agents/research/
# .agents/prompts/
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
- Constraints: 👤 HUMAN (from PROJECT_BRIEF.md)

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
- ADR: decisions/adr/000X-related.md
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

When creating files in `.agents/`, update `.agents/README.md`:

```markdown
# Agent Artifacts

Last updated: YYYY-MM-DD

## Active Plans
- [Feature Name](plans/YYYY-MM-DD-feature-name.md) - 🤖→👤 Brief description

## Research
- [Topic](research/YYYY-MM-DD-topic.md) - 🤖 Brief description

## Key Prompts
- [Auth exploration](prompts/auth-exploration.md) - Prompts that led to ADR-0005

## Archived
- [Old Plan](plans/YYYY-MM-DD-old.md) - Superseded by [New Plan]
```

### Prompt Archive Format

When a significant decision is made based on AI exploration, archive the key prompts:

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

## Human Refinement
@evan: "Also need to support HIPAA compliance for healthcare clients."

## Final Decision
See ADR-000X for the decision outcome.
```
