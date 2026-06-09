---
name: audit-rust-contracts
description: Audit prompt for Rust API and type hygiene — fallible unwraps, unjustified unsafe, missing #[must_use], context-erasing errors, blocking-in-async, unbounded fan-out
stacks: rust
---

# Stack Audit: Rust Contracts and Type Hygiene

You are auditing this Rust codebase for API and type-contract hygiene: places where the type system, error handling, or async model has been short-circuited in a way that hides failure or erases context. This is a stack-specific audit — it runs only on repos that contain Rust.

## What to look for

### Fallible paths hidden behind unwrap / expect
- `.unwrap()` or `.expect()` on `Result`/`Option` in library, handler, or request-path code (tests and one-time startup code are lower priority)
- `.unwrap()` on lock poisoning, channel sends, or parsing of external input — these panic on real-world conditions
- A `?`-able call rewritten as `.unwrap()` because the surrounding function returns `()` instead of `Result` (the missing error type is the real bug)

### Unsafe without justification
- `unsafe` blocks with no `// SAFETY:` comment stating the invariant being upheld
- `unsafe` used to dodge the borrow checker rather than for a genuine FFI / layout / aliasing need
- Transmutes, raw-pointer deref, or `from_raw_parts` where a safe abstraction exists

### Missing #[must_use] on contract-bearing returns
- Functions returning a `Result`, a builder, a guard, or a value whose whole purpose is to be inspected, with no `#[must_use]` — callers can silently drop the result
- Types that represent a pending effect (a guard, a permit, a transaction handle) without `#[must_use]`

### Error types that erase context
- `Box<dyn Error>` or `anyhow::Error` at a public API or module boundary where a typed error enum belongs (boundaries are contracts)
- `.map_err(|_| ...)` that discards the source error instead of chaining it (`#[source]` / `.context(...)`)
- A single catch-all error variant absorbing causes that callers need to distinguish

### Blocking calls inside async
- `std::fs`, `std::net`, `reqwest::blocking`, `std::thread::sleep`, or CPU-heavy loops inside an `async fn` without `spawn_blocking`
- Holding a `std::sync::Mutex`/`RwLock` guard across an `.await` point

### Unbounded concurrency
- `futures::future::join_all` / `try_join_all` over a caller-sized or unbounded collection — should be `buffer_unordered(N)` or a semaphore
- `tokio::spawn` in a loop with no bound on in-flight tasks

## What to do

For each finding:
1. Name the file, line, and function
2. State the failure mode in production terms (panic on bad input, dropped result, thread-pool starvation, OOM under load)
3. Propose the fix: thread a `Result` + typed error, add `// SAFETY:`, add `#[must_use]`, `spawn_blocking`, or bound the fan-out with a concrete N

## Scope

Default: the whole crate workspace. Prioritize request handlers, async tasks, and public crate APIs; deprioritize tests and build scripts.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P4 (boundaries are contracts), P7 (every exception is an event), P8 (concurrency is bounded).
- Flag unbounded fan-out and blocking-in-async as HIGH priority — these are production incident candidates under load.
- Findings open an issue or a draft PR. Never auto-merge and never auto-apply a generative refactor.
