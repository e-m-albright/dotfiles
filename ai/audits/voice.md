# Audit: Voice — sycophancy, hedging, overconfidence, LLM cadence

The **stochastic half** of the voice article. A wordlist (`just lint-prose`) catches
banned phrases deterministically; this catches what a wordlist cannot — *tone*. Run
on a docs/PR-body/comment diff, on demand or nightly. **Advisory, never blocking**:
tone is a judgment call, so it informs a human, it doesn't fail a build.

## Scope

Generated or edited prose that lands in the repo or a PR: commit bodies, PR
descriptions, docs, code comments, READMEs. Not chat (ephemeral), not quoted
examples (a doc may legitimately quote slop to forbid it).

## What to flag

1. **Sycophancy.** Praise that does no work — "Great choice", "Excellent point",
   "You're absolutely right", reflexive agreement before a correction. Flag any
   affirmation that could be deleted with zero information loss.
2. **Hedge-everything.** Confidence sanded off every claim — "it might possibly",
   "this could perhaps potentially", stacked qualifiers. The reader can't tell what
   the author actually knows. Flag clusters of hedges on a verifiable fact.
3. **Overconfidence.** The opposite failure — asserting as certain something the
   author hasn't verified ("this fixes it", "this is fully secure") with no evidence.
   Calibration means stating what you know, flagging what you don't.
4. **LLM cadence.** The structural tells a wordlist misses: rule-of-three everywhere,
   "Not only X but also Y" scaffolding, a summary paragraph restating what was just
   said, em-dashes as connective tissue at high density, every section opening with a
   throat-clear. Flag the pattern, not a single instance.
5. **Empty intensifiers.** "very", "really", "truly", "incredibly" doing the work a
   precise word should. Flag when removing the intensifier strengthens the sentence.

## How to report

Per finding: `file:line` · which category · the offending text · a tighter rewrite.
End with a one-line verdict — *clean / minor / needs-a-pass* — and the single highest-
leverage rewrite. Do not rewrite the whole document; show the author the pattern and
let them fix it. Default to charity: technical terseness is not slop.

## Calibration

- **clean** — a grumpy senior engineer would not comment on the prose.
- **minor** — a few deletable affirmations or intensifiers; fix inline.
- **needs-a-pass** — pervasive hedging/sycophancy/cadence; the prose obscures the
  content. Hand back with the top 3 patterns named.
