# Code-Health Findings Ledger — `cli/`

The durable memory for code-health passes on the `dotfiles` CLI. Every
`/converge` (or `/code-health`) run **reads this first**
(skip anything Tolerated; don't re-litigate), then **writes back**: mark items
fixed, append newly-discovered, and re-rank the backlog. Numbers live in
[`baselines.json`](baselines.json); the graded snapshot in `report-<date>.md`;
the *why* behind Tolerated items in [`docs/adr/`](../../adr/).

Severity: **will-drift** (silently rots) · **friction** (slows change) · **aesthetic**.

---

## Run log

- **2026-06-07** — first measured pass (engine: converge). Baseline graded **B+** ([report](report-2026-06-07.md)). Landed: −6 stale `type:ignore` (shutil.which), narrowed broad `except` in `_parse_plugins_yaml`, single `VENDORS` registry, SSH-key fail-fast fix (+regression test). Suppressions (combined) 24→17. Seeded this ledger + baselines.
- **2026-06-07** (cont.) — complexity pass: decomposed all 6 at-ceiling functions; **ratcheted `cognitive_max` 10→9** (gate `complexipy src -mx 9`). The ceiling is now genuinely tighter — any new cc-10 function fails CI.
- **2026-06-11** — fleet-cohesion pass (engine: code-health). Graded **B+ → A−** ([report](report-2026-06-11.md)). Landed: (1) `agent.surface_path()` — doctor + overview probes now resolve vendor paths from the registry, not literals (backlog #2 substantially closed); (2) **fixed `agent verify` crash on a live MCP 405** — `HttpError` moved into the HttpClient port contract; (3) `config.load_config` catches `OSError`; (4) codex TOML array bracket-corruption bug fixed; (5) `SkillsSummary` made registry-driven — gemini/pi/hermes skill counts now visible in verify, two counting paths merged into one; (6) VENDOR_SETUP↔registry drift-guard test; (7) removed a `type:ignore` (`toml_value` made public). Ratcheted **type-ignore 16→15, cast 35→31**. +46 tests.
- **2026-06-11** (cont.) — Fable-5 review + backlog burn-down. Ran a Claude Fable 5 adversarial assessment ([artifact](fable-assessment-2026-06-11.md)); verified its findings before acting. Landed: (1) **SECURITY — closed `rm -rf` bypasses** in `guard-destructive-shell.sh` (flag order, quotes, long flags) + a 29-vector behavioral test suite (`test_guard_hooks.py`); the safety floor is now proven, not just wired; (2) **observability** (backlog #1) — structlog at boundaries/error points in `brew/service.py`, `lib.py`, `overview.py` (incl. logging the silent probe-read degradation); (3) **settings typed-boundary** (backlog #2) — `_subobj`/`_str_list` accessors in `claude.py` dedupe 13 JSON-boundary casts. Ratcheted **cast 31→21**. +29 tests (975 total). Also: statusline rate-limits → `% used`; `/consult --fable` backend.

---

- **2026-06-11** (cont.) — **fleet rearchitecture (engine: Fable-5 redesign).** Root cause of the cockpit's recurring self-contradictions diagnosed and removed: the same (vendor, surface) fact was computed in 10+ unsynchronized places with three skill denominators ([diagnosis](../../../ai/artifacts/fleet-rearchitecture-diagnosis.md), gitignored). Landed: (1) the **VENDORS registry now owns STANCE** — `Deploy(path, proof)` / `Native(note)` / `Local(why)` per surface (absorbing `_LOCAL_ONLY`, `_MCP_AGENTS`, the hand-written `_deploy_statusline`/`_deploy_permissions` dicts, `SURFACE_PATHS`); (2) **`fleet.py`** — one probe engine computes HAVE live; `build_fleet` **raises** on HAVE⟹CAN violations (consistency by construction, plus `test_have_implies_can_for_the_whole_registry` covering all 7 capability surfaces — supersedes `test_deploy_path_implies_capability_support`); (3) **every view is a projection** — uniformity, vendor pages (all 8 surfaces, Local reasons shown instead of bare n/a), hooks matrix (now probes the LIVE deployed configs, not repo sources), MCP applies-set (derived from mcp-servers.json targets — exposing that codex's old red ✗ was itself drift: granola never targeted codex); (4) **one skill census** (`skill_census.py`: ours/external/foreign vs canonical) ends the 38-vs-54-vs-36+18 hermes split and the false "45/36 drift" on every vendor — drift now fires only when canonical skills are missing; (5) truth fixes: pi hooks/statusline are real deploys (safe-git.ts/git-status.ts we link), agy statusline is `Native`, cursor's hooks path now points at the live plugin config (the old `.cursor/cli-config.json` probe never contained them). Deleted: `AgentVerifyService`, `SkillsSummary`/`RulesSummary`, `section_rules`. +~40 tests (1058 total).

- **2026-06-12** — backlog burn-down (engine: code-health router). Read-ledger-first pass; no re-diagnosis. Landed: (1) **gitleaks full-history secret scan** — `.github/workflows/gitleaks.yml`, weekly cron + dispatch, detection-only (the CI grep only ever saw the working tree; this repo is PUBLIC); (2) **doctor ↔ packages.toml drift gate** — `test_tool_checks_stay_in_sync_with_packages_toml`: every `brew install` hint in `_TOOL_CHECKS` must name an enabled manifest package (cask hints must be cask/auto), closing the unenforced CLAUDE.md invariant; (3) **ledger reconciled** — two gap items were already fixed in-tree but never marked (sensitive-file guard vector suite via `1e9e775`; clean-machine CI job via `016a172`).

## Open backlog (deferred — address when touched or in a focused pass)

Ranked by churn×complexity / drift risk.

**The product is outside the measurement system (Fable's biggest-risk finding).** Every gate/ratchet targets the ~9k-LOC Python CLI; `install.sh`, `macos/*.sh`, the guard hooks, and deployed vendor configs have ~no behavioral verification. The items below reflect that. Verified against source where actioned; see [fable-assessment-2026-06-11.md](fable-assessment-2026-06-11.md) for the full review.

1. ~~**Probe cells + registry reach**~~ **✅ SUBSTANTIALLY DONE (2026-06-11, fleet rearchitecture)** — stances/probe specs live in the registry; applies-sets derived; `Have` is a 4-state (`present|partial|empty|missing`). Residual: an unreadable file still collapses to "not deployed" (logged, not surfaced as `error`) — revisit only if a real misdiagnosis occurs.
2. ~~**doctor ↔ packages.toml sync**~~ **✅ DONE (2026-06-12)** — drift gate `test_tool_checks_stay_in_sync_with_packages_toml` (doctor/test_doctor_core.py): every brew hint in `_TOOL_CHECKS` must name an enabled manifest package. Scope note: the inline Runtimes hints (go, etc.) sit outside the declarative table; extend only if one actually drifts.
3. **Capability matrix is doc-mirrored** · friction — `capability_matrix.py` and the `agent-fleet.md` table are two hand-authored copies; the drift test parses the markdown. Generate the doc table from the Python matrix (`agent docs --check`) instead. (Fable #5.)
4. **Glyph dicts scattered** · clarify · *aesthetic* — status→glyph maps duplicated across `doctor/cli.py`, `agent/cli.py`, `console.py`; centralize. Low value.
5. ~~**Observability integration**~~ **✅ DONE (2026-06-11)** — structlog at boundaries/error points in brew/lib/overview; the silent probe-read degradation now logs.
6. ~~**Settings typed-boundary**~~ **✅ DONE (2026-06-11)** — `_subobj`/`_str_list` accessors dedupe the claude.py JSON-boundary casts (cast 31→21). lib.py was already down to 2 (JSON-decode boundary, Tolerated).
7. ~~**VendorPaths home-dir centralization**~~ **✅ SUBSTANTIALLY DONE (2026-06-11)** — `agent.surface_path()`; remaining literals are genuinely probe-specific. Drift-guard test added.
8. ~~**Dedup in overview rendering**~~ **DEFERRED — wrong-abstraction risk** — the `_render_*matrix` builders are distinct column shapes; merging would be the wrong abstraction (Metz).

### Shell / product-coverage gaps (Fable §2 — outside every current gate)
- ~~**`guard-sensitive-file.sh` untested**~~ **✅ DONE (was already fixed `1e9e775`, ledger reconciled 2026-06-12)** — 21-vector suite in `test_guard_hooks.py`; basename matching closed the bare/relative `.env` bypass.
- ~~**No clean-machine CI**~~ **✅ DONE (was already fixed `016a172`, ledger reconciled 2026-06-12)** — `clean-machine` job rehearses `agent setup` / `overview` / `verify --offline` / `doctor` against a fresh `$HOME`; traceback = fail. Residual (still open): full `install.sh` is macOS-specific and not rehearsed.
- ~~**gitleaks history scan**~~ **✅ DONE (2026-06-12)** — `.github/workflows/gitleaks.yml`: weekly scheduled `gitleaks` over full history (fetch-depth 0), detection-only.
- **Shell scope under `docs/health/`** — script count / max-LOC / shellcheck-errors-blocking ratchet; shellcheck currently runs non-blocking.
- **skill_stats scheduling** — telemetry exists (dead skills, weak triggers) but is manual; wire it weekly to drive curation. (Fable §2.5.)
- **coverage_pct not ratcheted** — 85% is a static floor, not monotonic.

## Tolerated (by design — do NOT re-propose; see ADR)

- **Per-vendor setup modules kept separate** — not consolidated to a generic+config driver. Wrong-abstraction risk. → [ADR-0001](../../adr/0001-keep-per-vendor-setup-modules.md). **Revisit trigger ("past a 6th vendor") fired and retired 2026-06-11**: Hermes is the 6th; reviewed and the split still holds (hermes.py is a 60-line skills-only module with no MCP/hooks/rules logic to share). Decision unchanged.
- **`settings_merger.py` generic `dict[str, Any]` + its 2 `type:ignore`s** — load-bearing for a generic JSON-merge utility; verified pyright-required. Swapping for `cast` would be type-laundering.
- **`_AgentChoice` explicit StrEnum** — duplicates the `VENDORS` names, but typer needs concrete members for `--help`/completion; dynamic enum risks introspection breakage.
- **`skill_stats.py` defensive JSON `cast` accessors** — the transcript schema is undocumented/shifting; the casts are the typed boundary.

## Dismissed this run (investigated, not real)

- **`RemotePane._status` thread race** — `_apply_status` is marshalled via `call_from_thread`; no cross-thread write. (debugger-confirmed false positive.)
- **`action_reload` agent scan after `SessionError`** — `live_agents()` is independent of the session list; benign ordering, not a bug.

## Dismissed 2026-06-11 (investigated, not real)

- **`agent verify` "43/34" skill drift** — not a bug. Deployed counts include vendor/plugin skills beyond our canonical 34 (e.g. plugin-provided skills in `~/.claude/skills`). The line reports real state; only the "drift" label is slightly misleading (see backlog: relabel deployed-beyond-canonical as "extra"). gemini shows a clean 34/34.

## Adversarial-assessor findings — adapters/http.py (2026-06-11)

First run of the new `adversarial-assessor` skill (opus pass over `http.py` + the port contract). Verified before recording:
- **[H1] non-JSON 2xx branch uncovered** · *will-drift* — `probe_mcp`'s `except ValueError` (reachable-but-non-JSON) had no hermetic test; `FakeHttpClient` can't raise `ValueError`. **✅ FIXED** — added `_HttpNonJson` + `test_probe_http_non_json_body_is_reachable`.
- **[H2] `dict[str, Any]` return is a lie behind a suppression** · *friction* — `get_json`/`post_json` annotate `dict` but `json.loads` can return a list/scalar; papered with `# type: ignore[no-any-return]`. **✅ FIXED (2026-06-11)** — `_send` validates via a module-level `TypeAdapter(dict[str, object])`, raising `HttpError` on a non-object (or malformed) body; the `# type: ignore` is gone. (Chose the typed-adapter over a bare `isinstance` guard: strict pyright rejects returning a narrowed-from-`Any` dict, and `cast`/`type:ignore` are both at-ceiling ratchet families.)
- **[H3] `HttpError` dual import path** · *aesthetic* — `http.py` re-exported it in `__all__` while the port owns it. **✅ FIXED (2026-06-11)** — dropped from `__all__` (kept the internal import for raising); `test_http_adapter.py` now imports it from `ports`. `ports` is the single public path.
- **[H4] protocol-conformance tests near-vacuous** · *aesthetic* — name-only `isinstance` checks read stronger than they are. **✅ FIXED (2026-06-11)** — kept (it honestly guards the protocol's method *set* — a real regression catch if `run` is renamed) but strengthened with a missing-method negative case and an honest docstring scoping it to names; signatures stay covered by the adapter tests + pyright.

## Adversarial-assessor findings — agent subsystem + this session's work (2026-06-11)

Fable-5 pass over `cli/src/dotfiles/cmd/agent` (the verify-before-done hook, `agent instructions`, the ENGINEERING.md reorg). Full report under `docs/health/assessments/` (gitignored, ephemeral). Verified before acting; the headline finding was real and high-leverage.
- **[F1] verify-claims patterns false-block innocent prose** · *will-drift* — confirmed: `tests?` matched the "test" in "la**test** passing"; "it works" hid in "comm**it works**"; a *question* ("confirm it works?") and a prior-state report both tripped it. **✅ FIXED** — `\b`-anchored, declarative-only patterns + 4 regression allow-vectors. Also fixed a **latent hook bug it exposed**: the grep fed comment lines as patterns, so a commented-out paren crashed the match and failed open — the hook now strips `#`/blank lines as its header always claimed.
- **[F2] hook shipped to Codex on an unverified transcript schema** · *will-drift* — it polices unverified "done" claims while itself being one. **✅ FIXED** — scoped to Claude Code only (pulled from `codex/hooks.json`); comment documents the schema assumption.
- **[F3] `SubagentStop` uncovered** — a subagent's "all tests pass" reaches the orchestrator unchecked. **✅ FIXED** — same hook wired to `SubagentStop` (Claude).
- **[F4] P8 violated ENGINEERING.md's own binding law** (`— (review)` = no gate). **✅ FIXED** — the law now admits review (Tier B) as enforcement where the property is irreducibly semantic; P8 cites it.
- **[F5] est_tokens note overclaimed "name + description only"** (measures whole frontmatter). **✅ FIXED** — relabelled "skill metadata". Also fixed stale "umbrella" wording in `catechism.py`.
- **[F6] K/P/G IDs are position-mapped, no drift gate** · *will-drift* — **✅ P/G GATED (`test_engineering_map.py`)**; the manifest's `P{n or 12}`/`G{n or 14}` fallbacks **fixed** (now render `P?`/`G?`, never a fabricated count). **K-leg Tolerated** — `rules.md` has no K-markers and the manifest/test hardcode `K1-K8`; the kernel is a deliberate fixed 8-article set changed only by hand, so a count derived from `rules.md` buys little. Revisit only if the kernel gains numbered markers.

## Round 2 — assessor re-run on the hardened code (2026-06-11)

Confirming pass after the round-1 fixes ([report](../assessments/), gitignored). It found no new defects in the fixed code — the surviving signal is about the hook's *observability*, plus a cheap honesty cluster. Acted on:
- **[R2-telemetry] the hook's firing was unobservable** · *will-drift* — an unfired safety gate is itself an unverified done-claim. **✅ FIXED** — blocks now append to `$VERIFY_LOG` (default `~/.claude/verify-before-done.log`, opt-out `/dev/null`); tests assert it logs on block and stays silent on allow.
- **[R2-recall] flagship sign-off missed** — "All 975 tests pass" (count form) didn't match. **✅ FIXED** — added `\b(all )?\d+ tests? …\b` + a block vector; kept "+29 tests (975 total)" as an allow-vector (count report ≠ claim).
- **[R2-drift] gate re-implemented the prod regex** + **fabricating fallback** + **footer overclaim**. **✅ FIXED** — drift gate imports `_NUMBERED_HEADER`; columns render `P?`/`G?` on zero (tested); the budget footer now states it excludes the system prompt / auto-memory / vendor skills.
- **[R2-liveness] nothing verifies the Stop hook is *live* on the machine** (settings drift → K1 gate silently off forever) · *will-drift* — **TOP BACKLOG, verified.** The single biggest residual risk. Fix: a deployed-settings probe in `agent verify` that parses `~/.claude/settings.json` and asserts the Stop/SubagentStop entries. Deliberate feature (couples `verify` to Claude's settings schema) — left for a focused pass, not built autonomously. **Review trigger: 2026-07-11** (one month) — by then `verify-before-done.log` shows whether the gate ever fired; if blocks ≈ 0, reconsider the hook per ADR cadence.
- **Verified-but-dismissed:** any-tool predicate "near-vacuous" (R2 §1.1) — **kept as conservative v1**; the telemetry above is the precondition to revisiting it (don't build verifying-tool classification — that's the false-block trap). `_McpServersFile` RootModel "ceremony" — kept (load-bearing for strict pyright). `~/dotfiles` hardcoded hook paths (R2 §2.4), `>500`-line / meta-line transcript edges (§2.5), double-notify (§2.6) → backlog (conservative-direction / pre-existing repo convention).
