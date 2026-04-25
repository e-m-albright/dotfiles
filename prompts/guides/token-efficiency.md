# Token Efficiency & Model Performance

> **Last reviewed**: 2026-04-24 — Refresh when new research or tools emerge.

Strategies for reducing token consumption while improving model output quality. Less context, better results — backed by research.

---

## Core Principles

```
Less input → better reasoning (Levy et al., ACL 2024)
Middle context → systematically missed (Liu et al., TACL 2023)
Forced brevity → +26pp accuracy (March 2026 study via caveman)
Fewer tools → better instruction following (EASYTOOL, 2024)
```

**The counterintuitive finding**: Giving the model *less* to work with often produces *better* results. Every unnecessary token in context competes with the tokens that matter.

---

## Input Token Efficiency

### System Prompt Discipline

For every line in a system prompt or CLAUDE.md, ask: **"Would removing this cause a concrete mistake?"** If not, cut it.

| Practice | Impact |
|----------|--------|
| Prune CLAUDE.md ruthlessly | Prevents instruction dilution |
| Load tools/skills on-demand, not upfront | Reduces per-turn token cost |
| Use deferred tool loading | Schemas only when needed |
| Prompt caching for stable prefixes | 90% cost reduction on cached reads |
| Compress context semantically | 40-58% reduction, 100% fact preservation |

**Each tool definition costs**: 346+ base tokens + schema per request. In a 20-turn agentic loop, 10 unnecessary tools = ~7,000+ wasted tokens.

### Smart Context Selection

- **Agentic search > RAG**: Let the model find what it needs via grep/glob rather than dumping chunks
- **Sub-agents for research**: Investigation in a separate context window reports back a summary, keeping the main session clean
- **Clear between tasks**: Kitchen-sink sessions are the #1 performance killer

### Semantic Compression (Input)

Tools like [caveman-compression](https://github.com/wilpel/caveman-compression) strip predictable grammar from context:

```
Before: "In order to optimize the database query performance, we should
         consider implementing an index on the frequently accessed columns"

After:  "Need fast queries. Check which columns used most. Add index
         to those columns"

Result: 29% token reduction, 100% factual preservation
```

Three methods: LLM-based (40-58%), MLM-based (20-30%), NLP-based (15-30%).

---

## Output Token Efficiency

### Compression Techniques (Ranked by Aggressiveness)

| Level | Technique | Typical Reduction |
|-------|-----------|-------------------|
| 1 | "Be concise" in system prompt | ~10-20% (often ignored after a few turns) |
| 2 | Structured output formats (JSON/YAML) | ~30-40% |
| 3 | Pattern templates (`[thing] [action] [reason]`) | ~40-50% |
| 4 | Caveman-speak system prompts | ~65% (range 22-87%) |
| 5 | Ultra-compressed abbreviated syntax | ~70-80% |
| 6 | Fine-tuned terse models (oogaboogalm) | Baked into weights |

### The Caveman Approach

[Caveman](https://github.com/JuliusBrussee/caveman) (45k+ stars) forces compressed output:

```
Terse like caveman. Technical substance exact. Only fluff die.
Drop: articles, filler (just/really/basically), pleasantries, hedging.
Fragments OK. Short synonyms. Code unchanged.
Pattern: [thing] [action] [reason]. [next step].
```

Three intensity levels:
- **Lite**: Professional terseness, grammar preserved
- **Full**: Fragments, articles removed (default)
- **Ultra**: Maximum compression, abbreviated syntax

**Key finding**: Forced brevity doesn't degrade quality — a March 2026 study found it *improved* accuracy by 26 percentage points by reducing hedging and second-guessing.

---

## Task Decomposition

### Single-Responsibility Prompts

Kitchen-sink prompts (one session, many unrelated tasks) degrade performance because:
1. Context fills with irrelevant information from prior tasks
2. Model attention spreads across competing instructions
3. Errors compound without fresh-context checkpoints

**Pattern**: One task per session. `/clear` between unrelated work.

### Agent Orchestration Patterns

| Pattern | When to Use | Trade-off |
|---------|-------------|-----------|
| **Prompt chaining** | Fixed, sequential subtasks | Latency ↑, accuracy ↑ |
| **Router → specialist** | Input type determines handler | Separation of concerns |
| **Orchestrator-workers** | Unpredictable subtask breakdown | Flexibility, more tokens |
| **Fan-out parallelism** | Independent tasks | Speed, isolated context |
| **Writer/Reviewer** | Implementation + verification | Fresh-context review catches more |

### When Sub-Agents vs. Single-Pass

**Use sub-agents when:**
- Task reads many files (research, exploration)
- You want fresh-context review of your own output
- Multiple independent tasks can run in parallel
- Investigation would pollute the main implementation context

**Use single-pass when:**
- The diff fits in one sentence
- Scope is clear and small
- No exploration needed

---

## Model Routing

### Tiered Routing Strategy

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| Triage, classification, linting | Haiku | Fast, cheap, sufficient for simple decisions |
| Pre-commit hooks, formatting checks | Haiku | Sub-second, low cost |
| Code implementation, debugging | Sonnet | Best cost/capability ratio |
| Architecture, complex reasoning | Opus | Highest capability |
| Security review, threat modeling | Opus | Nuance matters, cost is justified |

**Rule of thumb**: Use the cheapest model that produces correct output for the task class.

### When More Tools/Context Hurts

Each additional tool or instruction:
1. Adds tokens (direct cost)
2. Increases decision-making complexity (indirect quality cost)
3. Pushes critical information toward the "lost middle" zone
4. Compounds across every turn of an agentic conversation

---

## Research & Evidence

### Key Papers

| Paper | Finding | Citation |
|-------|---------|----------|
| **Same Task, More Tokens** (Levy et al., ACL 2024) | Reasoning degrades at lengths far below technical maximums | Input padding hurts even when models "support" long context |
| **Lost in the Middle** (Liu et al., TACL 2023) | Information in the middle of long contexts is systematically missed | Put critical instructions at start and end |
| **EASYTOOL** (arxiv 2401.06201, 2024) | Compressed tool docs reduce tokens AND improve tool utilization | Fewer, better-described tools > many redundant ones |
| **Brief constraints + accuracy** (March 2026) | Brief response constraints improved accuracy by 26pp | Conciseness forces precision over hedging |

### Tools & Projects

| Tool | Stars | What It Does |
|------|-------|--------------|
| [Caveman](https://github.com/JuliusBrussee/caveman) | 45k+ | Output compression via system prompt (65% reduction) |
| [caveman-compression](https://github.com/wilpel/caveman-compression) | 800+ | Input context compression library (40-58% reduction) |
| [oogaboogalm](https://github.com/Mintzs/oogaboogalm) | 44 | Fine-tuned terse model weights |
| [laconic](https://github.com/GabrielBarberini/laconic) | 13 | Short common words, contextual brevity |

### Anthropic's Own Architecture Decisions

Claude Code's design validates these findings:
- **Deferred tool loading**: Schemas load on-demand, not all upfront
- **Sub-agent architecture**: Research in separate context, summary returned
- **Compaction via summarization**: Prunes conversation when context fills
- **`/clear` recommendations**: Fresh context between unrelated tasks
- **Prompt caching**: 90% cost reduction for stable prefixes (tools, system prompt)

---

## Deferred Plugins (Revisit List)

Disabled 2026-04-25 to reduce per-session token overhead. All still installed. Re-enable per-session with `/plugin enable <name>` or move back to always-on if the friction isn't worth the savings.

| Plugin | What It Does | Re-enable When |
|--------|-------------|----------------|
| **feature-dev** | Guided feature development with codebase understanding | Starting a new feature |
| **code-review** | PR code review | Reviewing PRs |
| **code-simplifier** | Post-implementation cleanup | After finishing implementation |
| **pr-review-toolkit** | Comprehensive PR review (5+ sub-agents) | PR creation or review |
| **claude-md-management** | CLAUDE.md audit and improvement | Maintaining CLAUDE.md files |
| **claude-code-setup** | Automation recommender for Claude Code | Setting up new projects |
| **agent-sdk-dev** | Agent SDK app development | Building SDK apps |
| **frontend-design** | Production-grade frontend interfaces | UI/frontend work |
| **playground** | Interactive HTML playgrounds | Creating explorers/tools |
| **security-guidance** | Security review guidance | Security review sessions |
| **explanatory-output-style** | Educational insights in every response | Learning/onboarding sessions |
| **data-engineering** | Airflow/pipeline management (20+ skills) | Data pipeline work |
| **notion** | Notion MCP integration | Using Notion |

**Gap**: Claude Code has no automatic plugin routing (detect task type, load relevant plugins). This is manual. If a plugin is needed >30% of sessions, it should be always-on. Revisit after 2-4 weeks of use to see which ones you keep re-enabling.

**Ideal future**: A lightweight hook or router that detects task type from the first user message and enables relevant plugins automatically. Similar to how Claude Code already defers tool schemas.

---

## Actionable Audit Prompt

Use this prompt to audit and prune a project's AI configuration for efficiency. Adapt the repo name as needed.

```markdown
## Task: AI Configuration Efficiency Audit

Audit this repository's AI agent configuration (CLAUDE.md, .ai/rules/,
skills, tools, MCP servers, hooks) for token efficiency. The goal is
fewer tokens in, fewer tokens out, better model performance.

### Phase 1: Measure Current State

1. Count total lines across all CLAUDE.md files (root + subdirectories)
2. Count total .mdc rule files and their combined line count
3. List all tools/skills currently loaded at session start
4. List all MCP servers configured
5. Identify any duplicate or near-duplicate instructions across files

### Phase 2: Prune System Prompts

For each line in CLAUDE.md and each .mdc rule, apply this test:
- "Would removing this cause a CONCRETE mistake?" → Keep
- "Is this general knowledge the model already has?" → Cut
- "Is this a preference that rarely matters?" → Cut
- "Is this duplicated elsewhere?" → Cut the duplicate

Report: lines before, lines after, what was cut and why.

### Phase 3: Audit Tool Loading

For each tool/skill that loads at session start:
- How often is it actually used? (check recent sessions if possible)
- Could it be deferred (loaded on-demand instead)?
- Is its description concise and unambiguous?

Report: tools before, tools recommended for deferral, description improvements.

### Phase 4: Consolidate Rules

- Merge .mdc files that cover overlapping topics
- Eliminate rules the model follows by default (don't instruct what's natural)
- Convert verbose rules to terse single-line directives

### Phase 5: Restructure for Cache Efficiency

- Stable content (tools, core rules) should come first (cached)
- Dynamic content (project-specific, changing) should come last
- Identify cache breakpoint opportunities

### Deliverables

1. Pruned CLAUDE.md (before/after line count, diff summary)
2. Consolidated .mdc rules (merged files, removed files)
3. Tool loading recommendations (defer, remove, keep)
4. Token budget estimate (before/after input tokens per turn)
```

---

## Quick Reference: Efficiency Checklist

Before shipping any AI configuration change, verify:

- [ ] CLAUDE.md is under 100 lines (each line prevents a concrete mistake)
- [ ] No duplicate instructions across CLAUDE.md and .mdc files
- [ ] Tools load on-demand where possible (deferred loading)
- [ ] Tool descriptions are concise (under 2 sentences each)
- [ ] Sub-agents handle research tasks (not the main session)
- [ ] Model routing matches task complexity (haiku/sonnet/opus)
- [ ] Stable prompt content is positioned for cache hits
- [ ] `/clear` is used between unrelated tasks
