---
name: skill-creator
description: Create new skills, modify and improve existing skills, and structure them for reliable triggering. Use when user wants to create a skill from scratch, edit/improve an existing skill, optimize a skill's description for triggering accuracy, or says "make a skill for X", "turn this into a skill", "improve this skill", "fix the trigger on this skill".
metadata:
  source_url: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
  source_commit: d211d437443a7b2496a3dad9575e7dddd724c585
  ported_at: 2026-05-07
  adaptations: Streamlined from 485 lines to ~230. Stripped sections requiring Anthropic's eval-runner infrastructure (run_loop.py, aggregate_benchmark.py, eval-viewer/, blind-comparison agents, packaging). Stripped Claude.ai/Cowork-specific sections. Kept the meta-knowledge (anatomy, progressive disclosure, writing patterns, style). Added pointers to our `dotfiles agent lint` validator and `skill-format.md`.
---

# Skill Creator

Create new skills and improve existing ones. The high-level loop:

- Decide what the skill should do and roughly how
- Write a draft
- Run the skill on 2-3 realistic test prompts (manually or via subagent)
- Read the outputs critically; rewrite
- Repeat until it works

Your job is to figure out where the user is in the loop and meet them there. They might be at "I want to make a skill for X" — start at the beginning. They might already have a draft — go straight to test/iterate.

This skill is the meta-skill. It complements:
- **[Skill format](references/skill-format.md)** — the convention spec for this repo (frontmatter, body, source attribution, tool restrictions). [Agent format](references/agent-format.md) covers subagents.
- **`dotfiles agent lint`** — the validator. Run it after every edit to confirm spec compliance.
- **`docs/skills-sources.md`** — the source-attribution registry. Add a row when porting from upstream.

## Creating a skill

### Step 1 — Capture intent

The current conversation often already contains the workflow the user wants to capture (e.g., "turn this into a skill"). Pull from history first — tools used, sequence of steps, corrections, input/output formats observed.

Confirm with the user:
1. What should this skill enable Claude to do?
2. When should it trigger? (Specific user phrases / contexts.)
3. What's the expected output format?
4. Should we set up test cases? Skills with **objectively verifiable outputs** (file transforms, data extraction, fixed workflow steps) benefit from test cases. Skills with **subjective outputs** (writing style, design) often don't need them — qualitative review is enough. Suggest the appropriate default.

### Step 2 — Write the SKILL.md

Use the canonical layout from `skill-format.mdc` (full conventions: [Skill format](references/skill-format.md); for authoring subagents instead, see [Agent format](references/agent-format.md)):

```
skill-name/
├── SKILL.md          (required — frontmatter + body)
├── scripts/          (optional — black-box executables)
├── references/       (optional — docs loaded on demand)
└── assets/           (optional — output templates)
```

Frontmatter (required: `name`, `description`):

```yaml
---
name: skill-name
description: <what it does>. Use when <literal user phrases / file types / scenarios>.
metadata:                       # only if ported/adapted
  source_url: ...
  source_commit: ...
  ported_at: YYYY-MM-DD
  adaptations: ...
allowed-tools: Read Grep Glob   # only for read-only skills
disable-model-invocation: true  # only for user-only-invoked skills
---
```

#### Description discipline

The description is the **primary triggering mechanism**. Claude has a tendency to *under-trigger* skills — the description should be a little **pushy**, naming literal phrases the user might say, file types, and concrete scenarios.

**Bad:** *"How to build a dashboard."*
**Good:** *"How to build a fast dashboard for internal data. Use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data."*

For skills at risk of false-firing on adjacent topics, include explicit `Do NOT trigger when …` or `SKIP:` clauses (Anthropic's `claude-api` description is the canonical example).

### Step 3 — Body conventions

- **Imperative voice.** *"Run the script"* not *"The user can run."*
- **Explain the why, not just the what.** LLMs are smart; rote `MUST` / `NEVER` directives are a yellow flag.
- **≤ 500 lines.** If exceeding, split into `references/` (linked one level deep).
- **No surprise.** A skill must not contain malware, exploit code, or anything that contradicts its stated intent. Roleplay/style skills are fine; deception is not.

### Step 4 — Progressive disclosure

Three loading levels:
1. **Metadata** (~100 tokens) — name + description, always in context.
2. **SKILL.md body** — loaded when the skill triggers (≤ 500 lines).
3. **Bundled resources** (`scripts/`, `references/`, `assets/`) — loaded only as needed.

Patterns:
- Reference files explicitly from SKILL.md: `[label](references/foo.md)` with guidance on when to read.
- For multi-domain skills, organize by variant under `references/`:
  ```
  cloud-deploy/
  ├── SKILL.md (workflow + selection logic)
  └── references/
      ├── aws.md
      ├── gcp.md
      └── azure.md
  ```
  Claude reads only the relevant reference file.
- For large reference files (>300 lines), include a table of contents.

### Step 5 — Black-box scripts

If bundling executable code in `scripts/`, **always** include this paragraph in SKILL.md:

> *DO NOT read the source until you try running the script first and find that a customized solution is absolutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.*

Always run scripts with `--help` first. Look for `--help` to surface options before improvising.

## Testing

### Test cases

After drafting, write 2-3 realistic test prompts — what a real user would actually say. Save to `evals/evals.json` if you want structured tests:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column for profit margin. Revenue in C, costs in D",
      "expected_output": "Spreadsheet with new column showing profit margin %",
      "files": [],
      "expectations": ["Output is a .xlsx file", "Includes new column with profit margin formula"]
    }
  ]
}
```

See [references/schemas.md](references/schemas.md) for the full schema (used by Anthropic's eval runner; we don't currently run it but the schema is the data contract for any future eval system we add).

**Bad test prompts:** "Format this data." "Extract text from PDF." Too abstract — won't reliably trigger or test anything.

**Good test prompts:** Concrete, specific, with file paths, column names, casual tone, real backstory. See the example above.

### Trigger queries

To validate the description triggers correctly without false positives, write 8-10 should-trigger prompts and 8-10 should-not-trigger near-misses. Save as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Negative cases must be **near-misses** — share keywords with the skill but actually need something else. Obvious irrelevance (e.g. "write a fibonacci function" for a PDF skill) tests nothing.

### Manual validation

If you don't have an eval runner, just do it manually:
1. Spawn a subagent with the skill loaded; give it a test prompt.
2. Spawn another subagent **without** the skill; same prompt.
3. Compare outputs.
4. Read both transcripts — note where the skill helped, where it confused the agent, where rote instructions made the agent waste time.

Alternatively, just describe each test case to yourself and see what Claude with the skill produces vs. what Claude without the skill produces. Less rigorous; works fine for low-stakes iteration.

## Improving the skill

### How to think about improvements

1. **Generalize from the feedback.** A skill is meant to be used many times across many prompts. If you and the user are iterating on a few examples and the skill works *only* for those examples, it's overfit. Watch for fiddly example-specific changes vs. principled changes.

2. **Keep the prompt lean.** Remove anything not pulling its weight. Read transcripts (not just outputs) — if the skill is making the model waste time on unproductive work, cut that part and re-test.

3. **Explain the why.** When you find yourself writing `ALWAYS`/`NEVER` in caps or rigid structures, that's a yellow flag. Reframe and explain the reasoning so the model understands why something matters. More humane, more powerful.

4. **Look for repeated work.** If 3 test runs all produced similar helper scripts, bundle that script in `scripts/`. Write it once; tell the skill to call it.

5. **Validate after every edit.** Run `dotfiles agent lint` to confirm the skill stays spec-compliant (frontmatter, "Use when" trigger, body length, caps count).

### The iteration loop

1. Apply your improvements.
2. Re-run the test cases (and the trigger queries if you have them).
3. Compare against the previous iteration — same test prompts, different outputs.
4. Get user feedback. Empty feedback = looks good.
5. Improve, repeat. Stop when:
   - User says they're happy.
   - Feedback is consistently empty.
   - You're not making meaningful progress.

## How skill triggering works

Skills appear in Claude's `available_skills` list with their name + description. Claude decides whether to consult a skill based on the description.

**Important nuance:** Claude only consults skills for tasks it can't easily handle on its own. Simple one-step queries like "read this PDF" may not trigger a skill even if the description matches perfectly — Claude can handle them directly. Complex, multi-step, or specialized queries reliably trigger skills when the description matches.

Implication: trigger eval queries should be **substantive enough that Claude would actually benefit from consulting a skill**. Test "make a 4-page PDF report from this CSV with a chart on page 2" not "open the PDF."

## Source attribution (when porting)

If you're adapting an upstream skill, add `metadata.source_*` to the frontmatter, a `## Sources` footer at end of body, and a row in `docs/skills-sources.md`. See `skill-format.mdc` § Source attribution for the convention.

## Sources
- Adapted from [anthropics/skills/skill-creator](https://github.com/anthropics/skills/blob/d211d43/skills/skill-creator/SKILL.md) (ported 2026-05-07, Apache-2.0). Streamlined to ~230 lines; stripped Anthropic's eval-runner infrastructure and Claude.ai/Cowork sections; pointed at our `dotfiles agent lint` validator and `skill-format.md`.
