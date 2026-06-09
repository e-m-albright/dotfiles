---
name: audit-bug-hunt
description: Correctness-defect hunt — off-by-one, race conditions, float money, error-path gaps, null/None handling, resource leaks, unbounded concurrency/recursion
---

# Correctness Audit: Bug Hunt

You are auditing this codebase for latent correctness defects — bugs that compile and pass the happy path but fail under edges, concurrency, or load. Serves **P7 (Every exception is an event)** and **P8 (Concurrency is bounded)**.

## What to look for

### Boundary & Off-by-One
- `<` vs `<=`, `len` vs `len-1`, inclusive/exclusive range confusion
- Empty-collection, single-element, and first/last-iteration edge cases

### Race Conditions & Temporal Bugs
- Check-then-act (TOCTOU) on files, cache entries, or DB rows without a lock/transaction
- Shared mutable state touched from multiple tasks/threads without synchronization
- Read-modify-write that isn't atomic

### Float Money & Numeric Precision
- Currency or quantities stored/computed as `float` instead of integer-minor-units or `Decimal`
- Accumulated rounding, `==` on floats, silent integer overflow/truncation

### Error-Path Gaps
- `except Exception` / `catch {}` that swallows and continues with a bad value
- Errors logged but the function returns as if it succeeded
- Retries with no backoff, no cap, or that retry non-idempotent operations

### Null / None / Undefined Handling
- Optional values dereferenced without a guard; `unwrap`/`!` on values that can be absent
- Default-on-missing that masks a real failure upstream

### Resource Leaks
- Files, sockets, DB connections, locks opened without a `with`/`defer`/`try-finally`/RAII
- Leaks on the error path specifically (acquired, then an exception skips release)

### Unbounded Concurrency / Recursion
- `gather` / `join_all` / fan-out with no semaphore or `buffer_unordered(N)`
- Recursion or growth with no depth/size bound on attacker- or data-controlled input

## How to report

For each finding: `file:line`, the defect class, **severity** (will-corrupt-data / will-crash / latent), the input or interleaving that triggers it, and the fix (guard, transaction, `Decimal`, bound, context manager). NEVER auto-apply a fix.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
