---
name: pr-greenlight-cycle
description: Use when iterating on a PR to get CI green and ready to merge. Enforces "verify locally first" discipline so you stop burning CI minutes (and cache cycles) discovering problems that local commands would have caught in seconds. Triggers on "get this PR merged", "monitor PR", "fix the failing checks", "why is CI red", or any iterative push-and-watch loop on an open PR.
---

# PR Greenlight Cycle

You are about to iterate on an open PR until CI is green. Most of the waste in this loop comes from one mistake: pushing first and asking CI what's broken, instead of running the same gate locally in 30 seconds.

## The rule

**Every push that has any chance of failing CI must be preceded by the local equivalent of the gate that would catch it.** The pre-commit and pre-push hook stages are not enough on their own. They are subsets, not parity. Run the actual CI gate locally before you push.

If you cannot reproduce a CI failure locally, that is a parity bug in the hook configuration. Fix the hook, do not paper over it with another push-watch loop.

## Local commands that mirror the merge-blocking gates

Build a mental map of (CI workflow) → (local command). Common patterns by stack:

| Stack | CI gate | Local command |
|---|---|---|
| Rust | clippy + tests | `cargo fmt --check && cargo clippy --workspace --all-targets -- -D warnings && cargo nextest run --workspace` |
| Python | ruff + type + tests | `ruff check . && pyright && pytest` |
| TypeScript / Web | biome + svelte-check / tsc + vitest | `biome check . && svelte-check && vitest run` (or `npm test`) |
| Generic | full preflight | `just verify` / `just check && just test` / project-specific umbrella |
| PR text / secrets / em-dash | hook scripts | trust the pre-commit hook for these — they're cheap |

If the change spans multiple stacks, run all the gates the diff touches, or call the umbrella recipe (`just verify`, `npm run preflight`, etc.) and call it done.

**Key parity points that bite repeatedly:**
- Test-feature flags: `--all-targets --features db` (Rust) vs plain `cargo check` — only the former catches lints inside `#[cfg(test)]`.
- Workspace scope: `--workspace` vs the current crate only.
- Type-check mode: `pyright` strict vs project default.
- Lint scope: lint-against-baseline vs lint-from-scratch.

## Workflow

1. **Identify the gate that will block your change.** Diff scope tells you this. A Rust-only change does not need to run the Web gate locally.
2. **Run that gate locally and watch it pass.** This is non-negotiable. If it does not pass locally, do not push.
3. **Push.**
4. **Watch the PR with `gh pr checks <num> --watch` or `--watch --interval 30`.** Do not use long-interval polls. `--watch` returns the moment the rollup flips. Run it with `run_in_background: true` if you need to keep working.
5. **If CI fails on a gate you did not run locally:** that is a process failure, not just a code failure. Add the missing local check to your routine and (if it is a recurring miss) propose a hook update.
6. **If CI fails on a gate you DID run locally:** that is a parity bug. Compare commands exactly. Common drift points: `--all-targets`, feature flags, workspace scope, strict mode.

## Anti-patterns to avoid

- **PR body churn.** Every edit to the PR body retriggers PR-text workflows. Refresh the body once, at the end, after the diff stabilizes. Sibling-agent pushes are not a reason to re-edit, only to re-read.
- **Long polling for CI status.** Setting a 5-10 minute wakeup to "check CI" is a smell. Use `gh pr checks <num> --watch` (foreground) or `run_in_background: true` (background) so you get notified the instant a check flips.
- **Trusting only the pre-commit hook.** Pre-commit hooks are fast smoke checks, not the full gate. Pre-push is closer to parity, but still subsets some checks for speed.
- **Pushing the fix before reading the failure.** Always pull `gh run view --log-failed --job=<id>` for the exact line first. Otherwise you'll fix the wrong thing.
- **Re-running CI to "see if it works now" without changing anything.** If you pushed nothing new, the result will be identical. Read the log instead.

## Sibling-agent races

If multiple agents are pushing to the same branch:

- `git fetch && git log --oneline origin/<branch> -5` before every push. If sibling commits landed, rebase or merge before pushing your fix.
- Commit your fix immediately when ready; do not let it sit while another agent's push absorbs it.
- If a sibling commit broke a gate, fix it forward and credit the cause in the commit message ("Sibling push abc1234 introduced X"). Do not revert sibling work.



## When a check fails repeatedly

Three failed pushes is a parity bug, not a flaky test. Stop the cycle and:

1. Diff the local command against the CI command character-for-character.
2. Look at `.github/workflows/*.yml` and the local hook config (`lefthook.yml`, `.husky/`, etc.) together.
3. Update the hook so the same failure cannot escape locally next time.

The goal is shoot-once-score, not push-watch-fix-push-watch-fix.
