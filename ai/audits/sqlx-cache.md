---
name: audit-sqlx-cache
description: Audit prompt for compile-time-checked query cache hygiene (sqlx-style) — stale committed query cache vs migrations, SQLX_OFFLINE build correctness, queries missing from the offline cache, cache/migration schema drift
stacks: rust
---

# Stack Audit: Compile-Time Query Cache Hygiene (sqlx-style)

You are auditing this Rust codebase for the integrity of its compile-time-checked query cache (the `sqlx`-style `.sqlx/` offline data, or equivalent). The cache is a checked-in artifact that must stay a faithful projection of the live schema: the build is only reproducible if the cache, the migrations, and the queries all agree. This is a stack-specific audit — it runs only on repos using compile-time-checked queries.

## What to look for

### Stale cache vs migrations
- The committed `.sqlx/` (or equivalent) cache reflecting an older schema than the latest applied migration — a column/table the cache still describes was changed by a later migration, or vice versa
- A migration that adds/renames/drops a column with no corresponding regeneration of the cached query metadata
- Cache files whose timestamps/content predate migrations that touch the same tables

### SQLX_OFFLINE build correctness
- CI that builds with `SQLX_OFFLINE=true` (or relies on the cache) but no step that *verifies* the cache is current — so a stale cache passes CI and only breaks against a live DB
- A build that silently falls back to a live-DB connection when the cache is missing, hiding the fact that offline data is incomplete
- `.sqlx/` (or the cache dir) gitignored or only partially committed, so offline builds depend on a developer's local state

### Queries not covered by the offline cache
- `query!` / `query_as!` / `query_scalar!` macro invocations with no matching entry in the committed cache — these force a live-DB connection at build time
- Newly added checked queries committed without their cache entries
- Dynamically constructed queries that skip compile-time checking entirely where a checked macro was feasible

### Cache ↔ migration schema drift
- The schema implied by the cached query metadata diverging from the schema the migrations actually produce (a column type, nullability, or name mismatch)
- More than one source describing "the schema" (cache, migrations, a hand-written struct) that can disagree — there must be one source of truth, with the cache derived from it

## What to do

For each finding:
1. Name the cache file / query macro / migration involved
2. State the failure mode: offline build breaks against a real DB, CI green on stale data, non-reproducible build depending on local DB state, or a runtime type mismatch the cache failed to catch
3. Propose the fix: regenerate the cache (e.g. `cargo sqlx prepare`) as part of the migration workflow, add a CI check that fails on a stale/incomplete cache, commit the missing entries, or make the cache a derived artifact of one schema source

## Scope

Default: the whole crate workspace plus the migrations directory and the committed cache dir. Prioritize the CI build configuration and any query added or changed since the last cache regeneration.

## Rules
- Do NOT change any code or regenerate the cache. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P1 (the compiler is the first reviewer), P3 (one source of truth per concept), and P6 (dead/stale artifacts are dead weight; the cache must be live and derived, not a drifting copy).
- Treat a stale or incomplete cache that can pass CI as HIGH priority — it defeats the entire point of compile-time checking.
- Findings open an issue or a draft PR (e.g. "regenerate query cache + add freshness check"). Never auto-merge and never auto-apply a generative refactor.
