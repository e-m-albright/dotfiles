# Code-Health Findings Ledger — `cli/`

The durable memory for code-health passes on the `dotfiles` CLI. Every
`/improve-codebase-architecture` (or `/code-health`) run **reads this first**
(skip anything Tolerated; don't re-litigate), then **writes back**: mark items
fixed, append newly-discovered, and re-rank the backlog. Numbers live in
[`baselines.json`](baselines.json); the graded snapshot in `report-<date>.md`;
the *why* behind Tolerated items in [`docs/adr/`](../../adr/).

Severity: **will-drift** (silently rots) · **friction** (slows change) · **aesthetic**.

---

## Run log

- **2026-06-07** — first measured pass (engine: improve-codebase-architecture). Baseline graded **B+** ([report](report-2026-06-07.md)). Landed: −6 stale `type:ignore` (shutil.which), narrowed broad `except` in `_parse_plugins_yaml`, single `VENDORS` registry, SSH-key fail-fast fix (+regression test). Suppressions (combined) 24→17. Seeded this ledger + baselines.

---

## Open backlog (deferred — address when touched or in a focused pass)

Ranked by churn×complexity / drift risk.

1. **Settings typed-boundary at call sites** · functional-core · *friction* — `cmd/agent/lib.py` accepts `env: dict[str,str]`; settings flow as dicts in places. Most of the 35 `cast` / 14 `Any` cluster lives here. Type the specific load sites (parse-don't-validate); leave the generic `settings_merger` helpers alone (Tolerated). Biggest suppression-metric mover.
2. **VendorPaths home-dir centralization** · domain-align · *will-drift* — `~/.claude`, `~/.codex`, `~/.agents`, `~/.cursor`, `~/.gemini`, `~/.pi` hardcoded across `vendors/*`, `verify.py`, `overview.py`, `doctor/service.py`. Extend the `VENDORS` registry with a paths accessor. High blast radius → its own pass.
3. **Observability integration** · (Tier-B/design) · *friction* — structlog is wired but barely used; `cmd/agent/lib.py`, `cmd/brew/service.py`, `cmd/agent/overview.py` have zero logging at service entry/error points. (U5 = C+, the lowest criterion.)
4. **Complexity-ceiling tidies** · tidy · *friction* — functions at cognitive-complexity 10: `setup_claude` (god orchestrator), `_apply_sessions`, `install_npm_globals`, `_install_external_skills`. Decompose one-per-commit; on churn hotspots, review with care.
5. **File-size extraction** · tidy/deepen · *friction* — `cmd/brew/service.py` (575), `cmd/agent/cli.py` (546) mix concerns; extract e.g. `InstallPlan` and CLI render helpers.
6. **Dedup in overview rendering** · tidy · *aesthetic* — 3 near-identical `_*_hook_events` and 3 `_render_*` table builders in `cmd/agent/{overview,cli}.py`; extract a generic helper (rule-of-three met).
7. **Glyph dicts scattered** · legible · *aesthetic* — status→glyph maps duplicated across `doctor/cli.py`, `agent/cli.py`, `console.py`; centralize. Low value.

## Tolerated (by design — do NOT re-propose; see ADR)

- **Five per-vendor setup modules kept separate** — not consolidated to a generic+config driver. Wrong-abstraction risk; revisit only past a 6th vendor. → [ADR-0001](../../adr/0001-keep-per-vendor-setup-modules.md)
- **`settings_merger.py` generic `dict[str, Any]` + its 2 `type:ignore`s** — load-bearing for a generic JSON-merge utility; verified pyright-required. Swapping for `cast` would be type-laundering.
- **`_AgentChoice` explicit StrEnum** — duplicates the `VENDORS` names, but typer needs concrete members for `--help`/completion; dynamic enum risks introspection breakage.
- **`skill_stats.py` defensive JSON `cast` accessors** — the transcript schema is undocumented/shifting; the casts are the typed boundary.

## Dismissed this run (investigated, not real)

- **`RemotePane._status` thread race** — `_apply_status` is marshalled via `call_from_thread`; no cross-thread write. (debugger-confirmed false positive.)
- **`action_reload` agent scan after `SessionError`** — `live_agents()` is independent of the session list; benign ordering, not a bug.
