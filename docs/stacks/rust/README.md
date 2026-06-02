# Rust

> Curated taste, not mandate — read this to derive per-project choices.

## Selection (pick / avoid / by phase)

### Phase 1 — Every Project

| Category | Pick | Avoid |
|----------|------|-------|
| Toolchain | **stable** | nightly (unless a dependency requires it) |
| Linter | **clippy** (warnings as errors in CI) | — |
| Formatter | **rustfmt** (never override) | — |
| Task runner | **Just** | Make (arcane) |
| Git hooks | **Lefthook** | Husky |

### Phase 2 — When Needed

| Need | Pick | Avoid |
|------|------|-------|
| Web framework | **Axum** | Actix (macro-heavy), Rocket (slower adoption) |
| Desktop app | **Tauri 2** | Electron (heavy, not Rust) |
| Async runtime | **Tokio** | async-std (smaller ecosystem) |
| Database | **SQLx** (compile-time checked SQL) | Diesel (compile times, macros) |
| Serialization | **serde + serde_json** | — |
| Config | **envy** (env vars → struct via serde) | config (complex YAML layering) |
| Domain errors | **thiserror** | manual `Error` impl |
| App errors | **anyhow** | `Box<dyn Error>` |
| Logging | **tracing + tracing-subscriber** | log + env_logger (less structured) |
| HTTP client | **reqwest** | hyper (low-level) |
| CLI | **clap** (v4; structopt merged in) | structopt |
| Hot reload (dev) | **cargo-watch** | — |

### Phase 2b — Data-Heavy Projects

| Need | Pick | Avoid | Notes |
|------|------|-------|-------|
| Full-text search | **tantivy** | Elasticsearch, Meilisearch | Embeds as a library, no separate service |
| CSV parsing | **csv** | — | Fastest parser, streaming support |
| XML parsing | **quick-xml** | xml-rs (slow) | Streaming, handles large files without loading into memory |
| HTML scraping | **scraper** | — | CSS-selector based, like Python's BeautifulSoup |
| SSE streaming | **async-stream** | — | Ergonomic `stream!` macro for Axum SSE responses |
| Vector embeddings | **pgvector** (via sqlx) | Qdrant, Pinecone | Keeps embeddings in PostgreSQL, no extra service |
| Validation | **validator** | — | Derive-based struct validation |
| Columnar analytics | **arrow + parquet + datafusion** | — | In-process OLAP/columnar in Rust — the Polars/DuckDB equivalent on the Rust side |

### Testing & quality

| Need | Pick | Avoid | Notes |
|------|------|-------|-------|
| Test runner | **cargo-nextest** | bare `cargo test` | ~1.5–3× faster, per-test isolation, flaky-retry. Keep a `cargo test --doc` step — nextest doesn't run doctests |
| Snapshot testing | **insta** (+ `cargo insta review`) | hand-rolled string asserts | For structured output: JSON responses, diagnostics, parser ASTs. Not for scalar asserts |
| Coverage | **cargo-llvm-cov** | tarpaulin (Linux-x86_64 only) | Source-based, cross-platform — works on macOS |
| Property testing | **proptest** | — | Generates inputs to falsify invariants |
| HTTP mocking | **wiremock** | — | Mock external HTTP in integration tests |
| Mutation testing | **cargo-mutants** | — | Periodic audit of test quality on critical modules — not an always-on gate |
| Supply chain | **cargo-deny** | cargo-audit alone | Advisories + license allowlist + bans + sources. See [security.md](../security.md) |

### Phase 3 — At Scale

| Need | Pick | Notes |
|------|------|-------|
| Observability | **OpenTelemetry** | Via tracing-opentelemetry; OTLP export to a collector (see [infrastructure.md](../infrastructure.md)) |
| Benchmarking | **criterion** | For performance-critical code; gate regressions in CI with **CodSpeed** |
| Fuzzing | **cargo-fuzz** or **bolero** | bolero unifies property + fuzz testing under one harness; cargo-fuzz for libFuzzer-style coverage-guided fuzzing |
| Docker build | **cargo-chef + mold** | chef caches the dependency layer; mold is a fast linker — together they cut Rust image rebuilds dramatically (see [infrastructure.md](../infrastructure.md)) |
| User docs | **Starlight (Astro)** | rustdoc for API docs |

## Idioms

### Hard rules

- No `.unwrap()` in production code — use `?`, `.expect("reason")`, or handle the case.
- No `unsafe` without a `// SAFETY:` comment explaining the invariant.
- No sentinel values (`-1`, null equivalents) — use `Option<T>` or `Result<T, E>`.
- No `.clone()` to satisfy the borrow checker — restructure ownership instead.
- All public types derive `Debug`. All fallible functions return `Result<T, E>`.
- Exhaustive pattern matching — no wildcard `_` on enums you control.
- `#[must_use]` on functions where ignoring the return value is likely a bug.
- Use `#[expect]` over `#[allow]` for suppressing warnings.
- Run `cargo clippy` and `cargo test` before committing.

### Ownership & borrowing

- Borrow by default, own by necessity. Accept `&str` not `&String`, `&[T]` not `&Vec<T>`.
- Use `impl AsRef<str>` or `impl Into<String>` for APIs accepting both owned and borrowed.
- When you need owned data, take `T` by value — makes cost visible at the call site.
- `Arc<T>` for shared ownership across async tasks; `Rc<T>` only in single-threaded contexts.
- If fighting the borrow checker, redesign data flow before reaching for `Clone` or `Rc`.

### Error handling

- **thiserror** for domain/library errors (typed, matchable variants).
- **anyhow** for application-level errors (context chaining).
- Always add `.context("what was happening")?` when propagating errors.
- Error messages describe what failed, not what to do.
- Panics mean "the program has a bug" — never for user errors or network failures.

### Async

- **Tokio** runtime. `#[tokio::main]` for entry, `#[tokio::test]` for tests.
- **tracing** + **tracing-subscriber** for structured logging.
- Use `.instrument(span)` for async functions — never `.entered()` in async (it's `!Send`).
- `tokio::task::spawn_blocking` for CPU-heavy work — never block the async runtime.
- `tokio::sync::Semaphore` for rate-limited concurrent operations.
- `tokio::sync::Mutex` over `std::sync::Mutex` when holding a lock across `.await`.
- `tokio::sync::mpsc` channels for producer/consumer pipelines.

### Type design

- Newtypes for domain concepts: `struct UserId(Uuid)` not bare `Uuid`.
- Enums over booleans: `Status::Active` not `is_active: bool`.
- Builders for types with >3 construction parameters.
- `From`/`Into` for natural conversions, `TryFrom` for fallible ones.
- Private fields with public constructors enforce invariants at creation.

### Naming

- `as_` (cheap ref-to-ref), `to_` (expensive new value), `into_` (ownership-consuming).
- Getters are the field name: `fn name(&self)` not `fn get_name()`.
- No Hungarian notation. Feature names without placeholders: `json` not `enable-json`.

### Common pitfalls

- Don't use `String` when `&str` suffices — pass borrowed, return owned.
- Don't default to `i32` for indexing — `usize` is the indexing type.
- Don't use `std::sync::Mutex` in async code — blocks the thread.
- Don't overchain iterators past 3-4 transformations — a `for` loop is clearer.
- Don't initialize-after-construct — objects should be usable when created.
- Don't use `Box<dyn Error>` — use `anyhow::Error` or a typed `thiserror` enum.
- `Vec::with_capacity(n)` / `String::with_capacity(n)` when size is known.

### Ask first

- Adding new dependencies.
- Changing database schema.
- Using `unsafe` code.

## Code patterns

### Newtype + enum domain modeling

```rust
struct UserId(Uuid);

enum Status {
    Active,
    Suspended,
    Deleted,
}
```

### Config via envy

```rust
#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    #[serde(default = "default_port")]
    pub port: u16,
    pub database_url: String,
    pub jwt_secret: String,
}

fn default_port() -> u16 { 3000 }

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        envy::from_env::<Config>().map_err(|e| anyhow::anyhow!("config error: {e}"))
    }
}
```

### Structured tracing

```rust
use tracing::{info, error, instrument};

#[instrument(skip(pool), fields(user_id = %id))]
async fn fetch_user(pool: &PgPool, id: Uuid) -> Result<User, sqlx::Error> {
    info!("fetching user from db");
    // ...
}

// Structured fields at call sites
info!(port = config.port, env = %config.env, "server starting");
error!(error = ?err, "request failed");
```

### Offload CPU work, rate-limit outbound calls

```rust
// CPU-heavy work off the async runtime
let parsed = tokio::task::spawn_blocking(move || parse_csv(&path)).await??;

// Rate-limit outbound API calls — Arc<Semaphore> in shared state
let permit = semaphore.acquire().await?;
```

## Project layout

Single crate:

```
src/
  main.rs          — entry point, server setup
  lib.rs           — re-exports, shared types
  config.rs        — settings via envy
  error.rs         — thiserror error types
  routes/          — HTTP handlers
  services/        — business logic
  db/              — database access
migrations/        — SQL migration files
```

Conventions:

- One module, one responsibility. Keep files under ~400 lines.
- `pub(crate)` for internal helpers; only `pub` what other crates need.
- Flat module trees. `routes/drugs.rs` not `routes/api/v1/drugs/handler.rs`.
- Use `[workspace.dependencies]` to pin shared dependency versions.

## See also

- [frameworks/axum.md](frameworks/axum.md) — Axum web APIs (extractors, error envelope, SQLx, SSE).
- [frameworks/tauri.md](frameworks/tauri.md) — Tauri 2 desktop apps (commands, state, events, IPC).
- [../../engineering-philosophy.md](../../engineering-philosophy.md) — universal code-health principles.
