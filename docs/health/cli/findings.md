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

## Open backlog (deferred — address when touched or in a focused pass)

Ranked by churn×complexity / drift risk.

**The product is outside the measurement system (Fable's biggest-risk finding).** Every gate/ratchet targets the ~9k-LOC Python CLI; `install.sh`, `macos/*.sh`, the guard hooks, and deployed vendor configs have ~no behavioral verification. The items below reflect that. Verified against source where actioned; see [fable-assessment-2026-06-11.md](fable-assessment-2026-06-11.md) for the full review.

1. **Probe cells: `present|absent|error`, and finish the registry reach** · align/will-drift — `overview.py` `_deploy_statusline`/`_deploy_permissions` are still hand-written 6-key dict literals (vs the registry-iterating siblings), and `render/overview.py` hardcodes `_MCP_AGENTS`/`_HOOK_AGENTS`/`_SUBAGENT_AGENTS` sets in the *presentation* layer. Cells are `dict[str,bool]`, collapsing unreadable into absent. Fix both at once: registry-derive the sets + the probe specs, switch cells to a 3-state enum. (Fable #2+#4; verified.)
2. **doctor ↔ packages.toml sync** · will-drift — `doctor/service.py` hardcodes 11 `_TOOL_CHECKS`; CLAUDE.md states doctor must stay in sync with `packages.toml` (the source of truth) but nothing enforces it. Add a drift test (or a `doctor=true` flag in the TOML). (Fable #3; CLAUDE.md invariant — verified.)
3. **Capability matrix is doc-mirrored** · friction — `capability_matrix.py` and the `agent-fleet.md` table are two hand-authored copies; the drift test parses the markdown. Generate the doc table from the Python matrix (`agent docs --check`) instead. (Fable #5.)
4. **Glyph dicts scattered** · clarify · *aesthetic* — status→glyph maps duplicated across `doctor/cli.py`, `agent/cli.py`, `console.py`; centralize. Low value.
5. ~~**Observability integration**~~ **✅ DONE (2026-06-11)** — structlog at boundaries/error points in brew/lib/overview; the silent probe-read degradation now logs.
6. ~~**Settings typed-boundary**~~ **✅ DONE (2026-06-11)** — `_subobj`/`_str_list` accessors dedupe the claude.py JSON-boundary casts (cast 31→21). lib.py was already down to 2 (JSON-decode boundary, Tolerated).
7. ~~**VendorPaths home-dir centralization**~~ **✅ SUBSTANTIALLY DONE (2026-06-11)** — `agent.surface_path()`; remaining literals are genuinely probe-specific. Drift-guard test added.
8. ~~**Dedup in overview rendering**~~ **DEFERRED — wrong-abstraction risk** — the `_render_*matrix` builders are distinct column shapes; merging would be the wrong abstraction (Metz).

### Shell / product-coverage gaps (Fable §2 — outside every current gate)
- **`guard-sensitive-file.sh` untested** — same class as the destructive-shell guard (now fixed + tested). Add a vector suite + harden globs.
- **No clean-machine CI** — nothing rehearses `install.sh` → `agent setup` → `doctor`. The single most credible gate the repo could add (Ubuntu degraded-mode job).
- **gitleaks history scan** — CI greps the working tree only; this repo is PUBLIC. Add one scheduled `gitleaks detect` over history. High severity / low effort.
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
