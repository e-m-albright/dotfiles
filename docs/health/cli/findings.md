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

---

## Open backlog (deferred — address when touched or in a focused pass)

Ranked by churn×complexity / drift risk.

1. **Observability integration** · (Tier-B/design) · *friction* — structlog is wired but barely used; `cmd/agent/lib.py`, `cmd/brew/service.py`, `cmd/agent/overview.py` have zero logging at service entry/error points. (U5 = C+, the lowest criterion.) Now the top backlog item.
2. **Settings typed-boundary at call sites** · purify · *friction* — `cmd/agent/lib.py` accepts `env: dict[str,str]`; settings flow as dicts in places. Most of the remaining `cast` (31) / `Any` (14) cluster lives here. Type the specific load sites (parse-don't-validate); leave the generic `settings_merger` helpers alone (Tolerated). Biggest remaining suppression-metric mover.
3. ~~**VendorPaths home-dir centralization**~~ **✅ SUBSTANTIALLY DONE (2026-06-11)** — added `agent.surface_path(home, vendor, surface)`; `doctor/service.py` (6 literals) and `overview.py` (statusline/permission settings probes) now resolve through the registry. Remaining literals (`.gemini/antigravity-cli`, `.pi/.../git-status.ts`, `.codex/rules/default.rules`, permission-policy files) are genuinely probe-specific, not registry-owned. Drift-guard test added.
4. ~~**Dedup in overview rendering**~~ **DEFERRED — wrong-abstraction risk** — post the render/ extraction, the `_render_*matrix` builders are distinct column shapes, not near-duplicates. Merging would be the wrong abstraction (Metz). Re-evaluate only at a genuine 4th near-identical builder.
5. **Glyph dicts scattered** · clarify · *aesthetic* — status→glyph maps duplicated across `doctor/cli.py`, `agent/cli.py`, `console.py`; centralize. Low value.

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
