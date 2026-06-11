---
name: adversarial-assessor
description: Route the work past an INDEPENDENT, stronger/different model acting as a skeptical principal engineer — the structural counter to model sycophancy. Spawns a fresh-context critic (default Claude Fable 5) read-only over a scope to surface what the author and their default agent are blind to, ranked by leverage, then treats every finding as a claim to verify. Use when the user says "adversarially assess this", "find my blind spots", "what am I missing", "stress-test the repo", "get a second model's brutal take", "audit with a different model", "poke holes in this", "is this actually good or are you just agreeing"; or after a big change when you want an outside opinion before trusting your own. Complements collaborative-ideation (your own sparring criteria) and /review (same-model diff review) — reach for THIS when the goal is to escape your own agreeableness by using a different model.
metadata:
  type: reference
---

# Adversarial Assessor

> **Why this exists.** Sycophancy is trained in by RLHF and cannot be prompted away — the research is blunt (even frontier models stay sycophantic ~29% of the time; "none eliminate it"). The durable counter is not asking the same model to be harsher; it is **routing the work past a different model, in a fresh context, with no stake in it.** That independent critic finds what the insider has normalized. In this repo it already earned its keep: a Fable-5 pass found a real `rm -rf` guard bypass the default agent had walked past.

## What it does

Runs a **skeptical principal-engineer assessment** of a scope (a repo, a subsystem, a diff) using an independent model — by default **Claude Fable 5** (`claude-fable-5`), the strongest public model, deliberately a *different* model than the one doing the work. Read-only. Output is four ranked sections (code health · risk/correctness · feature completeness · add/alter/cut with FOR/AGAINST/verdict), plus "3 things first" and the single biggest risk.

## How to run it

```
ai/skills/adversarial-assessor/scripts/assess.sh [focus text...]
ai/skills/adversarial-assessor/scripts/assess.sh --scope cli/src/dotfiles/cmd/agent  the agent subsystem
ai/skills/adversarial-assessor/scripts/assess.sh --model claude-opus-4-8  # cheaper assessor
just assess <focus>                                    # convenience wrapper (this repo)
```

It writes a timestamped report to `docs/health/assessments/` and prints the path. It calls a **paid model** (Fable 5 is $10/$50 per Mtok) under a budget cap, so it is opt-in and scoped, not a gate. Needs the `claude` CLI on PATH.

## The discipline (this is the load-bearing part)

1. **Findings are claims to verify, not gospel.** Apply the same skepticism to the assessor that it applies to the code. Before acting on any finding, check it against the actual source — confirm the bug reproduces, the bypass works, the coupling is real. In this repo's first run, the guard bypass was real and got fixed test-first; other findings were fair-but-deferred or wrong. Sort them yourself.
2. **Use a *different* model than the one being assessed.** The point is independence. Assessing Claude's work with Claude-default defeats it; Fable 5 (or Codex, or another vendor) is the move.
3. **Rank by leverage and irreversibility.** A verified safety/security/data bug outranks a style nit, always. Fix the irreversible-risk findings first.
4. **Record what you did with each finding** — fixed / deferred-with-reason / dismissed-as-wrong — in `docs/health/<scope>/findings.md`, so the next pass converges instead of re-litigating.

## When NOT to reach for it

- A routine pre-merge diff review → `/review` (same-model is fine for mechanical correctness).
- You already know the area is healthy enough → don't burn the spend to be told so. This is for when you suspect your own (or the agent's) confidence is unearned.
- Generating *new* design ideas collaboratively → `collaborative-ideation`. This skill attacks existing work; it doesn't brainstorm.

## See also
- `ai/agents/pi/extensions/consult.ts` — the narrow per-question version (`/consult --fable`) for Pi.
- `docs/health/` — where findings ledgers and prior assessments live.
