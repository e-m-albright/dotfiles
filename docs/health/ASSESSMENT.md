# Code-Health Book — Independent Assessment

> A critical, non-sycophantic review of the whole system (router + engine + lenses
> + canon + gates + persistent state + routines), commissioned to answer one
> question: *is this a near-perfect system for creating genuine gravity toward
> impeccable code health — such that "no human could do meaningfully better"?*
>
> Written 2026-06-07 after reading every skill, recovering the past incarnations,
> mapping every antagonist pair, and dogfooding the backbone on the `cli` scope.

## Verdict in one paragraph

This is a genuinely state-of-the-art, evidence-grounded, internally-consistent
**portfolio** — materially better than any single "refactor my code" tool and more
*honest* than commercial code-health products about what it can and cannot
guarantee. Its intellectual architecture (two orthogonal axes; the form/function
honesty that refactoring touches only Maintainability; antagonists arbitrated with
tiebreaks + ADR memory; "ratchet the unmeasurable via a recorded human decision")
is close to a local optimum **for a human-gated system**. But "no human could do
better" is the wrong frame and overclaims: the system is designed to *amplify a
disciplined human*, not replace one — and its own docs say so. The honest gap is
between the vision ("self-managing toward a global optimum") and what is actually
automated today: a local pre-commit ratchet, a one-shot bootstrap, and a
*documented-but-unwired* detection cadence. Magnetism toward good code: real and
well-engineered. Autonomous gravity that beats a good engineer: not yet, and by
design.

## What is genuinely excellent (steel-man)

1. **The two-axis model is novel and correct.** Convergent↔divergent × measured↔taste
   explains *why* one skill can't sit in two places, and the portfolio is the right
   shape for it. Most "code quality" frameworks are a single undifferentiated bag.
2. **Form/function honesty.** Stating up front that Tier-A refactoring is
   behaviour-preserving and therefore touches **only Maintainability** — that
   robustness needs Tier B + real tests, and refactoring can even *introduce*
   security regressions — is rare intellectual honesty. The book refuses to imply a
   guarantee it structurally can't make.
3. **Evidence base, not vibes.** Every major decision cites empirical work (the
   arXiv agentic-refactoring study on cosmetic unattended churn; CISQ/ISO 5055;
   CodeScene *Code Red*; GitClear duplication data; Buse-Weimer readability). The
   anti-pattern of weekly auto-merged generative refactoring is rejected *with a
   citation*.
4. **Anti-gaming gate design is battle-tested.** Monotonic ratchet + commit-trailer
   bumps, net-≤0-per-family, the type-laundering ban, `headroom 0` borrowed-credit,
   exact-fit-file trap — each closes a real exploit. This is the hard-won part.
5. **The canon is non-contradictory.** All five declared antagonist pairs
   (dedup↔decouple, deepen↔prune, tidy↔deepen, align↔prune, purify↔prune) are
   explicitly named with a decidable tiebreak, plus a catch-all "arbitration not
   accretion" + ADR log for novel conflicts. Verified pair-by-pair.
6. **It is dogfooded and it works.** The `cli` scope is a real worked example, and
   bootstrapping THIS session the ratchet immediately caught a genuine undercounting
   bug (a `**`-pathspec blind spot) — the system found a real defect in itself.

## Where reality trails the vision (the attack)

Ranked by how much they undercut the "self-managing gravity" claim.

1. **CI enforces the ratchet — RESOLVED (was the biggest gap).** As written, this
   said `.github/workflows/ci.yml` ran *zero* Python checks, so the ratchet/complexity/
   coverage floor lived only in local lefthook and was bypassable with `--no-verify`.
   Closed by commit `f0a8186`: the `cli` CI job now runs `just check` (the same recipes
   hooks run), so the floor is a CI-enforced invariant. Left here as a record of the
   gap and its fix. *Remaining nuance:* CI runs the **full** suite, not yet affectedness-scoped.
2. **`converge`↔`form-deepen` is the one ambiguous entry point.** `converge`'s
   description claims `form-deepen`'s exact trigger phrases ("this feels coupled", "where
   are the seams?", "deepen modules") with no scope signal in the phrase itself. The
   bodies disambiguate by scope+ratchet, but the *names* don't carry the
   measured-whole-repo vs taste-single-area distinction. This is the place a router
   is genuinely required.
3. **Mixed substrate is invisible to a newcomer.** The portfolio calls skills,
   slash-commands (`/review`, `/security-review`, `/simplify`), and subagents
   (`performance-engineer`) all "lenses" interchangeably. They're invoked
   differently, and nothing says which is which. `performance-engineer` is a
   subagent referenced as a Tier-B lens with no hint it isn't a skill.
4. **`form-purify` and `converge` are the weakest names.** `form-purify` reads as "remove
   impurities" — conceptually colliding with `form-prune` — rather than "isolate
   effects / extract a pure core." `converge` reads infrastructural/git rather than
   "the measured whole-repo engine." The other verbs (tidy/prune/clarify/align/
   deepen) are transparent.
5. **The ratchet is grep-based and therefore brittle.** No AST awareness: a pattern
   in a string, comment, or docstring counts. Dogfooding hit two instances (the
   `**` pathspec blind spot; a pattern catalog matching its own grep). It's an
   honestly-labelled proxy, but it *will* throw false signals — which is exactly why
   the human-gated arbitration around it is load-bearing, not optional.
6. **"Any repo" is really "any repo in our hand-coded languages."** The bootstrap's
   suppression catalog is Python/TS/Rust-flavoured; a Go or Ruby repo gets a
   near-empty ratchet. Language packs are a TODO, not a feature.
7. **Scheduled detection is documented, not wired.** No cron/remote agent exists yet
   — it's a policy plus building blocks. Honest, but it means a human still triggers
   everything except the local gate.
8. **The graded report is LLM judgment, not reproducible.** `report-<date>.md` can
   grade the same code differently across runs. The rubric + the (now-restored)
   worked example narrow the variance, but the "graded snapshot" is softer than the
   deterministic ratchet sitting next to it implies.
9. **No lens owns "speed" or "write tests."** A user who says "improve code health"
   but means "we have 0% coverage" is correctly *warned* (Tier A can't deliver
   robustness) but has nowhere in the portfolio to be handed to; `testing` /
   `test-driven-development` / `performance-engineer` live outside it.

## No ground lost vs past incarnations (confirmed + fixed)

Recovered and re-landed this session (were dropped in the rename/refactor):
the full suppression-marker catalog, the `# reason:` annotation rule, the 4th
stop-the-line alternative, decompose-untested-branch, "fix the crack you stumble
on / formally defer", the anti-gold-plating guard, and the worked
grade-calculation table. The U1–U11 rubric, structural-smell checklist, weights,
and calibration all survived intact into `review/references/health-rubric.md`.
One item consciously **not** restored: the old linear "grep for these tokens / wc
-l" grading *steps* — the new `review` fans out parallel audit threads, a strictly
better mechanism than a scripted grep walk, so retrofitting the step would fight
the new architecture.

## Bottom line for the owner

You have built the best *human-gated* code-health system I've seen, and the docs
are unusually honest about that scope. To close the distance to the "self-managing
gravity" framing, in priority order: **(1) enforce the ratchet in CI**, (2) resolve
the `converge`/`form-deepen` entry-point overlap and label the skill/command/subagent
substrate, (3) add language packs so "any repo" is true, (4) wire one real
scheduled detection routine. None of these are architectural rewrites — the
architecture is sound. They're the execution tail.
