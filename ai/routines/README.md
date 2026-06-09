# Routines — scheduled detection (L4)

Declarative scheduled scans that **detect, never fix**. The L4 layer of the
[defense-in-depth map](../../docs/knowledge/how-we-build.md): *schedule the finding,
gate the fixing.* A routine runs on a cron, audits the repo, and opens a draft PR or
issue with findings — a human decides what to act on. Generic by design: no project,
environment, or task-runner coupling.

| File | Role |
|---|---|
| [`registry.json`](registry.json) | one entry per routine: `cron`, `model`, `kind`, `audits`, `output`, optional `stacks` (affectedness) |
| [`protocol.md`](protocol.md) | the shared run loop every routine follows |

## How it's consumed

The registry is the declarative source; a cron runner (the `schedule` builtin, or a
CI cron) reads it, applies the affectedness gate, runs the `protocol.md` loop, and
surfaces findings. The routines reference the scanner library in [`ai/audits/`](../audits/)
(generic scanners run everywhere; `stacks:`-tagged scanners run only on a matching repo)
and the [`scorecard.sh`](../skills/converge/scripts/scorecard.sh) metric set.

## Why detection-only

Unattended *generative* refactoring on a cron is a cited anti-pattern: cosmetic churn,
~half the PRs needing fixes, no measured health gain, inter-pass oscillation. So the
cron is allowed to **find** (cheap, safe, reversible) and forbidden to **fix** (a
judgment call that stays with a human). Every taste/structural lens and all of Tier B
remain interactive. See [`CANON.md`](../../CANON.md) and the portfolio scheduling policy.
