# Agent Output Organization

## Directory: `.agents/`

All agent-generated artifacts MUST be placed in the `.agents/` directory at the project root. This keeps the main codebase clean and provides a clear audit trail of agent work.

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
├── sessions/                 # Optional: conversation logs
│   └── ...
└── README.md                 # Auto-generated index of contents
```

### Rules

1. **Never pollute the main tree** — Don't create random markdown files in `src/`, `docs/`, or project root
2. **Date-prefix files** — Use `YYYY-MM-DD-description.md` for chronological sorting
3. **Clean up scratch** — Delete scratch files after they're no longer needed
4. **Plans are immutable** — Once a plan is approved, create a new version rather than editing

### What Goes Where

| Content Type | Location | Example |
|-------------|----------|---------|
| Implementation plan | `plans/` | `2024-01-15-auth-system.md` |
| API research | `research/` | `2024-01-15-oauth-providers.md` |
| Code experiments | `scratch/` | `test-query.sql` |
| Debug notes | `scratch/` | `debugging-cors.md` |
| Architecture decisions | `plans/` | `2024-01-15-adr-database.md` |

### .gitignore Entry

Add to your `.gitignore`:

```gitignore
# Agent artifacts (optional - you may want to version plans/)
.agents/scratch/
.agents/sessions/
```

### Auto-Index

When creating files in `.agents/`, update `.agents/README.md` with:

```markdown
# Agent Artifacts

Last updated: YYYY-MM-DD

## Plans
- [Feature Name](plans/YYYY-MM-DD-feature-name.md) - Brief description

## Research
- [Topic](research/YYYY-MM-DD-topic.md) - Brief description
```
