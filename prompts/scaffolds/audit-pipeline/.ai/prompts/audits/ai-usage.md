# AI Usage Audit Synthesis

You are synthesizing findings from the ai-usage audit. The deterministic checks live in `scripts/audit/ai_usage.py` and have already produced `raw.json` plus per-check JSON.

## Inputs

- `raw.json` — overall status + per-check entries
- `token-budget.json` — token estimates for AGENTS.md, CLAUDE.md, GEMINI.md, and `alwaysApply: true` rules
- `frontmatter.json` — files in `.ai/` missing or malformed YAML frontmatter
- `dead-links.json` — broken relative markdown links across `.ai/` and AGENTS.md

## What to produce

Write `findings.md` alongside `raw.json`. Sections:

```markdown
# AI Usage Audit — <ts>

## Token budget
- **Always-on context**: <total> tokens across <N> files
- **Largest contributors**: [path → tokens]
- **Verdict**: under budget (<20k) / over budget — recommend trimming X

## Frontmatter
- [count] files missing or malformed frontmatter
- [list with file path and specific error]

## Dead links
- [count] broken relative links
- [list with source file → broken target]

## Recommendations
1. [Top 3 actions, ordered by impact-per-effort]
```

## Rules

- Do NOT modify any `.ai/` content. Findings only.
- For token-budget findings: identify the largest 2-3 files and propose what to cut, citing the principle of input token efficiency.
- For frontmatter: distinguish "missing entirely" from "malformed key" — they need different fixes.
- For dead links: distinguish "moved/renamed file" from "never existed" by checking git history.
- Reference `prompts/guides/token-efficiency.md` (in dotfiles) when explaining why budget matters.
