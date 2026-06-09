# Routine protocol — the shared scheduled-scan run loop

Every entry in [`registry.json`](registry.json) runs this loop. The invariant, from
the [Canon](../../CANON.md) scheduling policy and [how-we-build](../../docs/knowledge/how-we-build.md)
layer **L4**: **schedule the finding, gate the fixing.** A routine surfaces work; a
human decides what to act on. It enacts the kernel article *"detection is safe
unattended; the fix is human-gated"* and never auto-applies a generative refactor —
that pattern is empirically cosmetic, scope-creepy, and oscillating.

## The loop

1. **Affectedness gate.** If the routine declares `stacks`, skip it unless the repo
   has that stack — detected by a marker file (`Cargo.toml` → rust, `pyproject.toml`/
   `setup.py` → python, a `migrations/` dir or `*.sql` → sql). Generic routines (no
   `stacks`) always run. This mirrors the language-pack detection in
   `dotfiles agent health`.
2. **Fresh checkout.** Check out a scan branch off the default branch — never the
   working branch. The scan is read-only against source.
3. **Run.** If `scorecard: true`, run `ai/skills/converge/scripts/scorecard.sh --json`.
   For each name in `audits`, load `ai/audits/<name>.md` and run it as the model's
   instructions over the repo.
4. **Synthesize.** Merge findings; dedupe against the ledger; rank — churn×complexity
   for a `convergence` kind, severity for an `audit` kind. Mark each finding *known*
   (already in backlog), *tolerated* (with an ADR), or *new*.
5. **Write the ledger only.** Append the ranked, deduped findings to
   `docs/health/<scope>/findings.md`. This is the single file a routine writes.
6. **Surface.** Open a **draft PR** (`output: draft-pr`) or an **issue**
   (`output: issue`) carrying the findings. **Never auto-merge. Never auto-apply a
   refactor.**

## Hard rules (non-negotiable)

- **No source mutation.** The only file a routine writes is `findings.md` (the ledger).
- **Draft only.** A human reviews and decides; every taste/structural fix stays
  interactive.
- **Idempotent + de-duplicated.** Re-running re-discovers the same findings; dedupe
  against the ledger so the PR is signal, not noise.
- **No environment coupling.** A routine consumes only `ai/audits/*` + `scorecard.sh`
  + marker-file detection. No project-specific branch names, IDs, or task-runner
  recipes are baked in.
