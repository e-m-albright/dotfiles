# Fable 5 Adversarial Assessment — 2026-06-11

> External adversarial review by Claude Fable 5 (`claude-fable-5`), run read-only
> via `claude -p` as an independent assessor. Findings are *claims to verify*, not
> gospel. Status of each is tracked in [findings.md](findings.md). Verified items
> actioned this pass: the guard `rm -rf` bypasses (finding #1) — fixed + tested.

# Adversarial Assessment — /Users/evan/dotfiles (2026-06-11)

Independent skeptical read. Read-only; no changes made. Findings verified against source where cited (guard hooks, doctor, overview/render read directly; breadth via three parallel explore passes).

## Framing: the blind spot pattern

The repo's quality machinery (ratchet, complexipy, coverage, pyright) is aimed exclusively at `cli/src/dotfiles` — ~9k LOC of Python. But CLAUDE.md says "Primary language is Bash," and the actual *product* — `install.sh`, `macos/*.sh`, the security guard hooks, the deployed vendor configs — is outside every gate. The A− grade is real but scoped to the best-instrumented third of the repo. Everything below follows from that asymmetry.

---

## 1. CODE HEALTH — top 5 a strong reviewer still flags

**1. Security guard hooks have zero behavioral tests, and they have real bypasses.**
`ai/agents/shared/hooks/guard-destructive-shell.sh:30-33` — the filesystem case matches literal strings `rm -rf /`, `rm -rf ~`, `rm -rf $HOME`. Trivially bypassed by: `rm -fr /` (flag order), `rm -rf /*`, `rm -rf "$HOME"` (quotes), `rm -r -f ~`. The git regexes (lines 37-58) are better but untested — no vector for `git push -f origin main` vs `--force-with-lease`. The only "tests" verify the hook is *wired* (`test_agent_overview_core.py` intent checks), not that it *blocks*. This is the repo's hard safety floor and it is unproven. Same for `guard-sensitive-file.sh` globs.
**Fix:** a bats (or pytest-subprocess) vector suite — ~20 should-block / should-allow commands piped as JSON through each guard, asserting exit code. Wire into `just check`. Then fix the `rm` matching (normalize flags, or regex `rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+.*(/|~|\$HOME)`).

**2. The VENDORS registry's reach stops exactly where last week's pass stopped extending it.**
`cmd/agent/overview.py:237-257` — `_deploy_statusline()` and `_deploy_permissions()` are hand-written 6-key dict literals (`"claude": …, "hermes": False`), while `_deploy_rules/skills/subagents` iterate `VENDORS`. `render/overview.py:38-42` — `_MCP_AGENTS`, `_HOOK_AGENTS`, `_SUBAGENT_AGENTS` are hardcoded sets in the *render* layer (domain facts living in presentation). A 7th vendor added to `VENDORS` compiles, type-checks, and silently renders wrong. The 2026-06-11 report celebrates "extended the registry's reach" — these are the cells it didn't reach, and no gate notices.
**Fix:** push statusline/permission probe specs into the `Vendor`/`VendorPaths` registry (a probe callable or path+needle pair per vendor), derive the render sets from registry attributes, add the same drift-guard test pattern used for `VENDOR_SETUP`.

**3. Doctor contradicts the repo's own stated invariant.**
`cmd/doctor/service.py:13-25` hardcodes 11 tools. CLAUDE.md: "`macos/packages.toml` is the source of truth for what's installed. `dotfiles doctor` … must stay in sync with these lists." packages.toml carries ~100+ packages; there is no sync test between the two. The recent "declarative refactor" (`d8960eb`) made the hardcoding *tidier*, not *derived* — a band-aid the Canon itself prohibits (Article III.4: one source, generated outward).
**Fix:** parse packages.toml in doctor (a `doctor`-relevant subset can be flagged in the TOML, e.g. `doctor = true` per entry), or at minimum a drift test asserting every `_TOOL_CHECKS` command exists in packages.toml and every `[core]`-section package has a check.

**4. Silent degradation in probes — violates Canon III.9 in the layer that reports health.**
`cmd/agent/overview.py:_read_text` / `_file_contains` (≈lines 263-269 + the `except OSError: return ""` paths) collapse *unreadable* into *absent*. A corrupt or permission-broken `~/.claude/settings.json` renders as "statusline: not deployed" — the diagnostic tool misdiagnoses by design. Same shape in `_perm_codex`. "Fail loud, never silent in your own layer" is an article; the overview is the one place users look to learn truth about the fleet.
**Fix:** probes return a three-state (`present | absent | error`) instead of bool; render errors distinctly. The `dict[str, bool]` cells in `models.py` (e.g. `AgentPresenceRow.cells`) are the enabling primitive obsession — typing cells as `dict[Agent, ProbeState]` fixes both at once.

**5. The capability matrix is triple-maintained with a tautological drift guard.**
`cmd/agent/capability_matrix.py` (~310 lines) mirrors the hand-written table in `docs/knowledge/agent-fleet.md`, and the drift test parses the markdown table cell-by-cell. That's two hand-authored copies plus a test that breaks on doc formatting rather than on truth. Article III.4 says generate outward: the doc table should be *generated from* the Python matrix (`dotfiles agent docs --check` in CI), not hand-mirrored. Also: several "receipts" are `strings $(which agy) | grep` probes — they prove a string exists in a binary, not that a capability works; they will rot silently on vendor updates and the weekly `audit-agent-fleet-drift` is the only (stochastic) catch.
**Fix:** generate the markdown table from `CAPABILITY_MATRIX`; demote string-grep receipts to "weak evidence" status in the model so `--verify` reports confidence honestly.

(Skipped per findings.md: settings typed-boundary, observability, glyph dicts, render builders — all already ledgered.)

---

## 2. HEALTH-AUDIT GAPS

Ranked by what's uncovered, not generic:

1. **Shell is outside the entire measurement system.** No audit, no ratchet metric, no coverage, no complexity ceiling for the 21 scripts outside `cli/` (`install.sh` 400+ LOC, `macos/typewhisper.sh` 401 LOC). Shellcheck runs *non-blocking* (`|| true` in lefthook.yml, warning-level in CI). Add: a `shell` scope under `docs/health/` with its own baselines (script count, max LOC, shellcheck error count ratcheted to 0-blocking), plus the guard-hook vector suite from finding #1.
2. **No bootstrap/restore proof.** The repo's entire reason to exist is "rebuild a Mac" and nothing ever rehearses it. Even a partial CI job (Ubuntu container: `install.sh` in a degraded mode + `dotfiles agent setup --dry-run` + `dotfiles doctor`) would catch flow breakage. A `restore-rehearsal` audit prompt (quarterly: "could this repo rebuild a machine today? walk install.sh and flag rot") costs nothing.
3. **Deployed-state integrity.** Audits cover the *source* (`ai/`), nothing audits the *deployed* surfaces (`~/.claude`, `~/.codex`, …) for drift the CLI didn't cause — vendor auto-updates rewriting settings, plugins injecting skills, symlinks broken by vendor migrations. `agent verify` checks counts, not content hashes. Add a `deployed-drift` audit: diff deployed artifacts against canonical, flag third-party mutations.
4. **Secrets-in-history.** CI greps the working tree (advisory `::warning::` only — see `.github/workflows/ci.yml` lint job); gitleaks at commit is claimed in Canon III.6 but history is never scanned. One scheduled `gitleaks detect --log-opts` run; this repo is PUBLIC (per your own memory note), so this is the highest-severity gap per unit effort.
5. **Skill efficacy loop is open.** `skill_stats.py` (454 lines, real telemetry: dead skills, weak triggers, sequences) is manual-only. The library is curated on taste, not data. Schedule it weekly; land output in `docs/health/skills/`; let it drive pruning. Without this, the 34-skill library only grows.
6. **Coverage and mutation aren't ratcheted.** 85% is a static floor (`pyproject.toml`), not monotonic; mutmut is manual. Add `coverage_pct` to `baselines.json` (ratchet-check.sh already supports the pattern); promote mutation score to a scheduled audit with a recorded baseline — this was literally rec #3 of your own June research pass and is still unwired.
7. **Audit *prompts* have no landing zone.** 18 audits exist as prompts; their findings persist only if a human pastes them into findings.md. The Catechism says "schedule the finding" — but there's no `.github/workflows/audits.yml` or equivalent in-repo, and no convention for where, e.g., `voice.md` results accumulate. Either wire the cadence in-repo or document where the external scheduler's results land.

---

## 3. FEATURE / CAPABILITY COMPLETENESS

**Half-built (finish or kill):**
- **Verify-before-done gate** — your report's own #1 ROI item (sycophancy counter). Nothing started. A Stop-hook that checks the transcript's last assistant claim of "done/passing" against an actual tool-result is feasible today on Claude/Codex/Cursor.
- **skill_stats → curation loop** (above). Telemetry without a consumer is dead weight.
- **structlog** — wired, unused (ledger #1). Either instrument the service entry points or remove the dependency; a wired-but-silent logger is a competing version of "no logging."
- **fallbackModel** — decided "adopt," blocked only on picking the model. Pick Sonnet, ship it.
- **Hermes as a fleet member** — skills-only, no permissions, no guards, no statusline, hooks schema "undocumented, won't guess." Legitimate caution, but it means a sixth agent runs with *none* of the safety floor the fleet doc celebrates. Either invest (watch for its hooks schema to stabilize) or reclassify it out of the "fleet" framing so the uniformity claim stays honest.

**Over-built (YAGNI to cut or freeze):**
- **Capability-matrix receipts machinery** — 310 lines + probe registry + drift tests, for a matrix whose consumer is one human reading `agent capabilities` occasionally. The *deployment* matrices (overview) earn their complexity; the *vendor-support* matrix with provenance receipts is encyclopedia-keeping. Freeze it: stop adding receipt machinery, keep the doc.
- **Per-vendor statusline parity push** — four bespoke statusline implementations chasing a Pi reference design, including parsing "vendor-private" payloads by guessing field names (`ai/agents/gemini/statusline.sh`, per agent-fleet.md). That's drift-prone archaeology for cosmetics. Claude + Pi suffice; let Codex/agy run their native bars.
- **Six vendors, period.** The fleet doc shows Claude (full), Codex (full), Cursor (GUI, no telemetry, beta statusline), agy (workspace-local hooks declined, programmatic subagents), Pi (no MCP, no sandbox, ext-everything), Hermes (skills-only). Per your own memory, vendor-neutral CLIs were already rolled back once on subscription economics. The marginal cost of slots 5-6 is every drift test, matrix row, and doc section above. An honest question for the owner: what did Hermes or agy *produce* last month?

**Genuinely missing for a June-2026 harness:**
- **Clean-machine CI** (section 2, #2) — the single most credible gate this repo could add.
- **Deny-vocab behavioral parity test** — `test_deny_commands_sync.py` proves the *strings* exist per surface; nothing proves the *semantics* match (Gemini prefix-only vs Zed regex). A table-driven "would surface X block command Y" simulator would catch the documented gaps (pipe-to-shell absent on 3 of 5 surfaces) becoming silent regressions.
- **Cross-vendor rules-efficacy check** — you deploy one rules.md to six harnesses and never test whether any of them load it (a trivial "say orangutan" probe per vendor, scheduled — the proof-of-life hook already exists in the rules file and is exercised never).

---

## 4. SKILLS & TOOLS — add / alter / cut

| Proposal | For | Against | Verdict |
|---|---|---|---|
| **CUT `git-worktree-manager`** | 60-line wrapper over a 1-command CLI; `disable-model-invocation` means it's a man page | Cheap to keep; user-invoked only | **Cut.** `git worktree` help is better than a stale skill. |
| **MOVE `migration-writer`, audits `sqlx-cache.md`, `rust-contracts.md`, `migration-safety.md` to the project that uses them (Ophira)** | Goose/Drizzle/D1/sqlx are project-stack, not dotfiles; CLAUDE.md itself says stack opinions live in `docs/stacks/`, not deployed surface | They deploy globally so any repo benefits; near-zero token cost when unfired | **Move the skill; keep the audits** (audits cost nothing undeployed; the skill occupies the model's skill-selection budget on every session). |
| **MERGE `session-recovery` + `context-session-breakdown` + `workflow-closeout-learning`** | Three session-lifecycle skills, ~374 lines combined, overlapping triggers (handoff/crash/closeout); a model choosing between them mid-crisis is the worst time for taxonomy | They fire at genuinely different moments; merging risks a bloated router | **Merge to one `session-lifecycle` skill with three modes + references/.** Cuts ~200 lines of trigger surface. |
| **SPLIT the 250+ line skills (`agentic-e2e-debugging`, `workspace-health-audit`) into core + references/** | `converge` already proves the pattern in-repo; these are the 2 biggest token hits | Effort; references can go stale | **Do it.** Mechanical, pattern exists. |
| **ALTER `review` vs `code-reviewer` subagent dedupe** | Both do pre-merge correctness vs Canon; double-invocation yields duplicate findings | Deliberate inline-vs-dispatched split | **Alter, don't cut:** make `code-reviewer`'s prompt delegate its rubric to the `review` skill text so there's one rubric source (Article III.7). |
| **ADD guard-hook vector tests (CLI/justfile, not a skill)** | Finding #1; security floor unproven | None serious | **Add. First priority.** |
| **ADD `restore-rehearsal` audit prompt + clean-machine CI job** | The product is never tested | CI minutes; macOS runner cost (mitigate: Ubuntu degraded-mode) | **Add.** |
| **ADD scheduled skill-stats + dead-skill pruning report** | Closes the curation loop; code already exists | Scheduler dependency | **Add — wire, don't build.** |
| **DON'T BUILD per-vendor subagent config generator** | Report rec #5 says "do cautiously" | Only Claude/Codex/Cursor/Pi consume `.md` dirs and the `cp` loop already covers them; agy/Hermes are programmatic — there's no N to generate for | **Don't.** The cp loop *is* the generator. |
| **DON'T BUILD A2A/MCP gateway** | already correctly rejected | — | Concur. |
| **DON'T expand Hermes integration** | Sixth slot, skills-only, undocumented schemas | Optionality | **Freeze** until its hooks schema documents itself. |

---

## The 3 things I'd do first

1. **Behavioral test suite for the guard hooks + deny vocabulary** (bats or pytest-driven, vectors as data, wired into `just check`), then fix the `rm -rf` literal-match bypasses found above. The safety floor must be proven, not wired.
2. **A clean-machine CI job** that runs `install.sh` (degraded/Linux mode) → `dotfiles agent setup` against a fake `$HOME` → `dotfiles doctor`, plus the doctor↔packages.toml drift test. This converts the repo's core promise from claim to gate — exactly what the Canon demands of itself.
3. **Finish the registry**: move the `overview.py:237-257` dict literals and `render/overview.py:38-42` sets into the `VENDORS` registry with the existing drift-guard pattern, and switch probe cells from `bool` to `present|absent|error`. Closes findings #2 and #4 in one pass and makes vendor #7 (or vendor removal) a one-file change.

## The single biggest risk

**The measurement system audits everything except the product.** Every gate, ratchet, and graded report points at the 9k-LOC Python CLI — the *management layer* — while the things that actually touch the machine and gate destructive agent actions (bootstrap shell, guard hooks, deployed vendor configs) have zero behavioral verification and sit outside every baseline. The A− creates institutional confidence precisely where it's earned least. If `guard-destructive-shell.sh` has a bypass (it does) or `install.sh` rots (nothing would notice), the Canon's own standard — "if you cannot enforce it, do not claim it" — is currently being violated by the Catechism itself.
