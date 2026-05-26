# Agent Model Routing

How we choose between Claude Opus, Sonnet, and Haiku for our subagents. This is a calibration doc, not a strict policy — the harness inherits if `model:` is omitted, and most agents work fine on Sonnet.

## Tiers

| Model    | When                                                    | Examples (ours)                |
|----------|---------------------------------------------------------|--------------------------------|
| **Opus** | Architecture, security review, ambiguous reasoning, multi-step planning, high-stakes code review | _none currently — reserved for future_ |
| **Sonnet** | Default. Complex tasks needing real reasoning, code review, audits, hypothesis-driven debugging | `security-auditor`, `performance-engineer`, `debugger`, `error-detective`, `legacy-modernizer` |
| **Haiku** | Deterministic / single-tool / template-driven tasks. Specifically: when a senior engineer would write a 20-line script for it. | `shellcheck-reviewer` |
| **inherit** | Use the harness's default. Reasonable when the agent's reasoning depth varies wildly. | (case-by-case) |

## How to choose

Two questions:

1. **Does this agent need to reason about ambiguous design choices?**
   - Yes → Sonnet or Opus.
   - No (the recipe is well-defined) → Haiku.

2. **Does the agent's mistake have a high blast radius?**
   - High (production code review, security review of auth) → Opus.
   - Medium (most audits, RCA) → Sonnet.
   - Low (formatter, linter wrappers) → Haiku.

If the answer is *"this agent could be either"*, default to Sonnet. The cost delta vs. Haiku is small for episodic agent dispatch; the quality delta is sometimes large.

## Hybrid orchestration pattern

For multi-stage agentic workflows, mix tiers:

```
Planning (Sonnet)  →  Execution (Haiku)  →  Review (Sonnet/Opus)
         ↓                   ↓                       ↓
backend-architect → generate-endpoints → security-auditor
```

The expensive model picks the strategy; the cheap model executes; the expensive model verifies. Don't have all three stages on Opus.

## Why we differ from wshobson

[wshobson/agents](https://github.com/wshobson/agents) ships ~42 Opus, ~39 Sonnet, ~18 Haiku across 80 plugins. They're explicitly assigning by capability. We ship far fewer agents and our needs are narrower:

- We don't have agents for production deployment, blockchain, payment, or compliance — domains where wshobson reaches for Opus.
- Our review agents (`security-auditor`, `performance-engineer`) are scoped to feature-development context, not production audits — Sonnet is sufficient.
- We aggressively prefer Sonnet as the default. If we find a case where Sonnet is failing, that's the signal to escalate to Opus, not a default.

## Reviewing this doc

Revisit when:
- We add 3+ new agents (the tier mix may shift).
- Sonnet starts visibly failing on one of our agents (escalate that one to Opus).
- A new model tier ships (Sonnet 4.7, Haiku 4.6, etc. — re-baseline).
