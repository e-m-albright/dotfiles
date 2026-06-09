---
name: audit-sql-contracts
description: Audit prompt for SQL and query hygiene — string-built queries, N+1 patterns, missing indexes, SELECT * across boundaries, transactions spanning network calls, defaults absorbing schema drift
stacks: sql
---

# Stack Audit: SQL and Query Contracts

You are auditing this codebase for SQL and query-layer hygiene: places where queries are assembled unsafely, fan out per-row, scan unindexed columns, leak a `SELECT *` across a boundary, hold a transaction across a network call, or paper over schema drift with defaults. This is a stack-specific audit — it runs only on repos that issue SQL.

## What to look for

### String-built queries (injection surface)
- Queries assembled with f-strings, `+`, `.format()`, or template interpolation that splices a variable into the SQL text instead of using bound parameters / placeholders
- A dynamic `IN (...)` or `ORDER BY` built by concatenation from request input
- ORM "raw" escape hatches (`text()`, `query_raw`, `sql.raw`) carrying interpolated user input

### N+1 query patterns
- A query inside a loop over rows from a previous query — should be a join, an `IN` batch, or an eager-load/`prefetch`
- ORM lazy-loaded relationships accessed in a loop (the classic N+1)
- A per-item `await db.fetch(...)` inside an iteration over a collection

### Missing indexes on filtered columns
- Columns used in `WHERE`, `JOIN ... ON`, or `ORDER BY` on a large/growing table with no corresponding index in the schema/migrations
- A foreign key with no index backing it
- Composite filters whose column order doesn't match any index (or no composite index exists)

### SELECT * across a boundary
- `SELECT *` whose result crosses a module/service boundary or is serialized to an API response — the caller now silently depends on every column, and a schema change leaks through
- `SELECT *` feeding a model that only uses a few fields (over-fetch + fragile contract)

### Transactions spanning network calls
- A DB transaction held open across an HTTP request, queue publish, external API call, or `sleep` — holds locks and a connection while waiting on something it doesn't control
- A transaction whose body awaits unrelated I/O between the first write and the commit

### Defaults absorbing schema drift
- Read code that supplies a default when a column/key is missing (`row.get("col", fallback)`, `COALESCE` over a column that should always exist) — this silently masks a renamed/dropped column instead of failing loud
- Application-side defaults that diverge from the DB-side `DEFAULT`, so the source of truth is ambiguous

## What to do

For each finding:
1. Name the file, line, and the query (or call site)
2. State the consequence: injection vector, latency that scales with row count, full table scan under growth, leaked column contract, lock held across the network, or masked schema drift
3. Propose the fix: bind parameters, batch/join the query, add the index (name the columns), select explicit columns, move I/O outside the transaction, or remove the absorbing default and fail loud

## Scope

Default: the whole codebase. Prioritize hot read paths, request handlers, and anything taking external input into a query.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P4 (boundaries are contracts) and P8 (concurrency is bounded / hold no scarce resource across uncontrolled waits).
- Flag string-built queries with external input as HIGH priority (injection).
- Findings open an issue or a draft PR. Never auto-merge and never auto-apply a generative refactor.
