---
name: audit-migration-safety
description: Audit prompt for schema-migration safety — destructive migrations without expand-contract, editing applied (checksum-locked) migrations, non-backward-compatible drops absorbed by defaults, missing rollback, long-locking DDL on hot tables
stacks: sql
---

# Stack Audit: Schema Migration Safety

You are auditing this codebase's database migrations for deploy-time safety: migrations that can lose data, break a running deploy, lock a hot table, or silently diverge from already-applied history. Migrations are an append-only, immutable ledger — once applied they cannot be edited, and each one must keep the system runnable across the deploy window. This is a stack-specific audit — it runs only on repos with schema migrations.

## What to look for

### Destructive migration with no expand-contract path
- A `DROP COLUMN` / `DROP TABLE` / type-narrowing `ALTER` shipped in one step, with no prior backfill and no expand → migrate → contract sequence
- A rename done as drop+add (loses data) instead of add-new + backfill + dual-write + later-drop
- A `NOT NULL` added to an existing column with no backfill of existing rows first

### Editing an already-applied (checksum-locked) migration
- A migration file that has clearly already shipped (sequential number below HEAD, present in prior releases) being modified in this diff — frameworks that checksum applied migrations will refuse to run or, worse, silently skip it
- Renumbering, reordering, or rewriting historical migration files instead of adding a new forward migration

### Non-backward-compatible drop absorbed by a default
- Dropping/renaming a column that the *currently deployed* code still reads, where an application-side default (`row.get(col, fallback)`, `COALESCE`) hides the breakage instead of surfacing it — the deploy "works" while silently serving wrong/empty data
- A schema change that requires old and new app versions to coexist during rollout but isn't backward compatible (old pods break the moment the migration lands)

### Missing rollback / down path
- A forward migration with no corresponding down/rollback, in a system that expects reversibility, leaving no safe escape if the deploy fails
- An irreversible operation (data drop) with no explicit, acknowledged "this is one-way" note

### Long-locking DDL on a hot table
- `ALTER TABLE` that rewrites the table or takes an exclusive lock (adding a column with a volatile default on some engines, changing a type, adding an index non-concurrently) on a large/high-traffic table
- An index creation that isn't `CONCURRENTLY` (Postgres) / online, blocking writes for the duration
- A migration that holds a lock while also running a large backfill in the same transaction

## What to do

For each finding:
1. Name the migration file and the statement
2. State the failure mode: data loss, a checksum/ledger conflict, a broken rolling deploy, no way to roll back, or a write-blocking lock on a hot table
3. Propose the safe pattern: split into expand → backfill → contract across releases, add a new forward migration instead of editing history, make the change backward compatible for the deploy window, add a down migration, or use a concurrent/online/lock-free DDL form

## Scope

Default: the migrations directory plus the app code that reads the affected columns. Prioritize the migrations added or modified in the current diff and any touching a large/hot table.

## Rules
- Do NOT change any migration or code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P3 (one source of truth / immutable applied migrations) and P4 (boundaries are contracts; fail loud rather than absorbing drift with a default).
- Treat editing an already-applied migration and any unbackfilled destructive change as HIGH priority — these cause data loss or a stuck deploy.
- Findings open an issue or a draft PR proposing the expand-contract rewrite. Never auto-merge and never auto-apply a generative migration.
