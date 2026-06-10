# Code-Health Book — Session Handoff (2026-06-07)

Durable handoff for the next chat continuing the code-health book. Paste the
**Bootstrap Prompt** at the bottom into a fresh chat; the sections above are the
closeout evidence and learnings that back it.

---

## Closeout Audit — test posture (evidence-based)

Project gate: `cd cli && just check --fast` (fmt, ruff, pyright, deadcode, complexipy -mx 9, tests). Skill validation: `dotfiles agent lint`.

- **Unit** — **high.** `cd cli && uv run pytest -q` → **842 passed + 2 snapshots, ~12s.** Every module touched this session has tests: `test_skill_stats.py`, `test_brew_*`, `test_remote_service.py` (incl. the new SSH fail-fast assertion), `test_cli_agent.py`, `test_agent_setup_lib.py` (updated for the deploy remove-then-add), `test_skills_validate.py` (incl. the YAML-frontmatter regression), `test_doctor_*`.
- **Integration** — **medium.** Vendor setup is covered with fakes (`test_agent_setup_*`), but there's no full real-filesystem `dotfiles agent setup` end-to-end.
- **End-to-end** — **low.** Only typer `CliRunner`-level; no whole-CLI journey test.
- **Smoke** — **high.** `just check --fast` + `dotfiles agent lint` are the de facto smoke gates; both green.
- **Front-end (TUI)** — **medium.** Textual snapshot tests exist (2 passed); panes lightly covered.
- **User journey** — **low.** No scripted "adopt a repo → converge → ratchet" journey test yet.
- **Scripts** — **GAP (low).** `ai/skills/converge/scripts/scorecard.sh` and `ratchet-check.sh` have **no automated tests** — verified manually this session only. Highest-value coverage gap.

## Learning Artifacts (durable directives from this effort)

- **trigger:** mass find/replace across skill/doc files · **instruction:** never blanket-replace a token that can appear in prose or upstream URLs (e.g. `legible`→`clarify`, or any name inside a `github.com`/`mattpocock` attribution line); use per-line-guarded, targeted replacement and then run a relative-link check. · **scope:** repo · **strength:** hard-rule · **evidence:** BSD `sed \|` alternation silently no-op'd; a guarded Python pass + link check was the reliable path.
- **trigger:** renaming/removing a deployed skill · **instruction:** `npx skills add --copy` does NOT overwrite an existing dir and leaves stale old-name dirs; explicitly `npx skills remove <oldnames> -a <agent> -g -y` (claude-code + codex) before `dotfiles agent setup`. · **scope:** repo · **strength:** hard-rule.
- **trigger:** authoring a SKILL.md description · **instruction:** the `npx skills` CLI strict-parses YAML frontmatter and silently DROPS a skill on invalid YAML (e.g. an unquoted `: ` inside `description`); `dotfiles agent lint` now catches this — keep that check. · **scope:** repo · **strength:** hard-rule.
- **trigger:** acting on diagnostic-audit output · **instruction:** don't mass-execute it; arbitrate antagonist findings, prefer not churning, and verify each suppression is actually load-bearing (remove → run pyright) before deleting — swapping a `type:ignore` for a `cast` is forbidden type-laundering. · **scope:** task-type · **strength:** hard-rule.
- **trigger:** committing in this repo · **instruction:** the owner edits files in parallel; stage only your own paths, never `git add -A`. · **scope:** repo · **strength:** hard-rule.
- **trigger:** any assessment/review ask · **instruction:** be independent and critical, steel-man then attack; no sycophancy. · **scope:** global · **strength:** hard-rule.

## Recommended Formalization / Automation

- **Add tests for the scripts** (the gap): `scorecard.sh` + `ratchet-check.sh` — a pytest that shells out on a tiny fixture repo, or bats. Wire into `just check`.
- **Wire `ratchet-check.sh` as a gate** (advisory → blocking after a stability cycle) in `just` + CI, reading `docs/health/<scope>/baselines.json`.
- **Build `dotfiles agent health`** (open work below) and add a journey test: adopt → converge → ratchet.
- Keep `docs/health/<scope>/` + `docs/knowledge/code-health-portfolio.md` as the durable record; update them every pass.

---

## Bootstrap Prompt (paste into a new chat)

```
You're picking up a multi-session effort in the dotfiles repo (/Users/evan/dotfiles, a PUBLIC repo — no machine paths/secrets/"Ophira" in tracked files) to build a "code-health book": a portfolio of skills + measurement + memory that creates functional gravity toward impeccable, un-AI-slopped code and architecture. Work directly on main, small verified commits (commit email git@evanalbright.com; co-author trailer "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"). Be independent and critical, not sycophantic — the owner wants ground truth.

ORIENT FIRST (read, in order): docs/health/HANDOFF.md (this handoff); docs/knowledge/code-health-portfolio.md; docs/health/README.md + docs/health/cli/{baselines.json,findings.md,report-2026-06-07.md}; ai/skills/code-health/SKILL.md (router) and ai/skills/converge/SKILL.md (engine) + its references/ and scripts/; the six lenses ai/skills/{deepen,tidy,prune,clarify,align,purify}/SKILL.md; docs/engineering-philosophy.md + docs/knowledge/engineering-gates.md (the canon); ai/audits/* and ai/skills/review/references/health-rubric.md (diagnostics + U1–U11 rubric).

CURRENT STATE: 8-skill portfolio, recently renamed for clarity — umbrella `code-health` → engine `converge` (was improve-codebase-architecture) → six verb lenses `deepen tidy prune clarify(was legible) align(was domain-align) purify(was functional-core)`; Tier B reuses review/security-review/systematic-debugging/performance-engineer. Persistent backbone exists (docs/health/<scope>/ baselines+findings+report; ratchet-check.sh enforces; docs/adr/ for tolerated decisions). A real cli dogfood landed: graded B+, all cognitive-complexity-10 functions decomposed, gate tightened complexipy -mx 10→9. Deploy `dotfiles agent setup`; lint `dotfiles agent lint`; gate `cd cli && just check --fast` (842 tests green).

OPEN BUILD:
1. Build `dotfiles agent health` — CWD-based bootstrap (ProcessRunner has no cwd, so operate on the current repo). Runs scorecard, writes docs/health/<scope>/baselines.json + findings.md skeleton, prints "run /converge to grade." Deterministic core in the command; grade/findings stay with the engine. Add service + test + README mention; cc ≤9; full gate green.
2. Self-managing routines: wire the ratchet as a CI/hook gate; scheduled DETECTION runs (scorecard + audits → issue/draft PR, never auto-apply generative refactors); a one-command "adopt this repo" path. Replicable with zero re-specification.
3. Add the missing script tests (scorecard.sh, ratchet-check.sh).

REVIEW & INDEPENDENT ASSESSMENT (the heart of the session):
4. Review the whole book end-to-end; give your own verdict on whether it is — in breadth, depth, execution — a near-perfect system creating genuine gravity toward impeccable code health, the polar opposite of AI slop ("no human could do meaningfully better"). Steel-man, then attack. Name every gap/redundancy/weak seam/failure mode.
5. Verify NO GROUND LOST vs past incarnations: old code-quality-audit (U1–U11) → ai/skills/review/references/health-rubric.md; old .ai/rules/process/code-health.mdc → engineering-philosophy.md + engineering-gates.md. Recover originals via `git show 0dd6a8d^:.ai/skills/code-quality-audit/SKILL.md` and `git show 0dd6a8d^:.ai/rules/process/code-health.mdc`; confirm every criterion/principle survived + was supplemented, or fix.
6. Verify the philosophy is NON-CONTRADICTORY — a cohesive coding canon/catechism. Lenses contain deliberate antagonists (dedup↔decouple, deepen↔prune, DDD↔YAGNI); confirm each is explicitly arbitrated (tiebreaks + rejected-decision log), not unmanaged. Produce the single canonical statement of the canon if missing.
7. Make it HUMAN-INTERPRETIBLE + SELF-DOCUMENTING: propose (and on approval implement) the naming/ontology giving instant purpose/role clarity, tiering, and hierarchy legible to humans AND agents — across umbrella/engine/lenses/Tier-B/canon/scripts/state; showcase the distinct ENTRY POINTS (when to reach for which). Current names are a first cut; pressure-test whether the ontology is the clearest possible or propose better.

CONVENTIONS: SKILL.md format per ai/skills/skill-creator/references/skill-format.md; after skill edits run `dotfiles agent lint`; for renames, `npx skills remove <oldnames>` then `dotfiles agent setup`; dogfood the book's own skills; never auto-run generative refactors unattended; stage only your own paths (owner edits in parallel); ask before mass renames or new skills.

VERIFY: `cd cli && just check --fast`; `dotfiles agent lint`; `ai/skills/converge/scripts/ratchet-check.sh docs/health/cli/baselines.json` (from cli/).

FIRST THREE ACTIONS: (a) read the ORIENT files + run the VERIFY commands to confirm green; (b) recover the two past incarnations and diff against current to confirm no lost ground; (c) draft the naming/ontology + entry-point map and the non-contradiction check, then proceed to build `dotfiles agent health`.

DONE = bootstrap command shipped+tested+deployed; routines designed (wired where safe); script tests added; an honest written assessment with a gap list; confirmation (with fixes) that nothing was lost and the canon is non-contradictory; an owner-approved naming/ontology + entry-point map. Update docs/health + the portfolio doc as the record.
```
