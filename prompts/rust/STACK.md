# Rust Stack

**Philosophy**: Safe, fast, explicit services. Zero-cost abstractions, no runtime surprises.

## Runtime & Tooling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Rust Channel** | stable | Never use nightly in production services. |
| **Edition** | 2021 | Latest stable edition with improved closures, `use` imports. |
| **Async Runtime** | Tokio | De facto standard. Axum, SQLx, and the ecosystem are built on it. async-std is fragmented. |
| **Linter** | clippy | Built-in, comprehensive, no configuration needed to start. |
| **Formatter** | rustfmt | Built-in, zero config. `rustfmt.toml` only for minor preferences. |
| **Git Hooks** | Lefthook | Parallel execution, Go-based, YAML config. Consistent with other recipes. |
| **Task Runner** | Just | More readable than Makefiles. Consistent with other recipes. |
| **Hot Reload** | cargo-watch | Watches for file changes and reruns `cargo run`. |

## HTTP Framework

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **HTTP Framework** | Axum | Built by the Tokio team. Tower ecosystem. Type-safe extractors. No macro magic. |
| **Middleware** | tower + tower-http | Composable, reusable. Axum uses Tower natively — CORS, tracing, compression included. |

> **Axum vs Actix-web**: Axum is simpler and more idiomatic. Actix's actor model adds complexity without benefit for most services.
> **Axum vs Warp**: Axum's ergonomics are significantly better. Warp's nested-filter style is harder to read and extend.

## Database & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **SQL** | SQLx | Compile-time verified SQL. Async. No ORM abstraction hiding queries. |
| **ORM** | (none by default) | SQLx raw queries are clear and fast. Add SeaORM only for complex domain models. |
| **Migrations** | SQLx migrate | Built into SQLx — one dependency. |
| **Database** | PostgreSQL | Industry standard for production workloads. |
| **Connection Pool** | PgPool (SQLx) | Built-in to SQLx, async-native. |

## Serialization & Validation

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Serialization** | serde + serde_json | Universal standard. Every Rust library integrates with serde. |
| **Validation** | validator | Struct-based validation with derive macros. |
| **UUIDs** | uuid (v4) | Standard. Use `features = ["v4", "serde"]`. |
| **Dates / Times** | chrono | Standard. Use with `features = ["serde"]`. |

## Error Handling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Domain errors** | thiserror | Clean derive macro for typed errors. Industry standard. |
| **Propagation** | anyhow | Ergonomic `?` propagation in handlers and main. |

> **Pattern**: Define typed errors with `thiserror` in service/repository layers. Use `anyhow` at application boundaries (handlers, main). Convert between them with `From` impls.

## Configuration & Environment

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Config** | envy | Simple, serde-based. Deserializes env vars directly to structs. |
| **Secrets** | environment variables | Never embed in code. Load via `envy`. |

## Logging & Observability

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Logging** | tracing | Async-aware, structured, ecosystem standard. `log` is sync-only and less expressive. |
| **Subscriber** | tracing-subscriber | Flexible output: pretty for dev, JSON for production. |
| **Metrics** | prometheus/client_rust | Industry standard. |
| **Tracing** | OpenTelemetry | Vendor-neutral. Use `tracing-opentelemetry` bridge. |

## Testing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | built-in `#[test]` | No extra dependencies needed. |
| **Async tests** | `#[tokio::test]` | Built into the tokio crate. |
| **Mocking** | mockall | De facto standard for trait-based mocking. |
| **HTTP testing** | axum-test or httpx | Test handlers directly without binding to a port. |
| **Integration** | testcontainers-rs | Real PostgreSQL in tests via Docker. |

## Security

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Vulnerability scanning** | cargo-audit | Checks against the RustSec advisory database. |
| **JWT** | jsonwebtoken | Well-maintained, serde integration. |
| **Password hashing** | argon2 | Recommended by OWASP. bcrypt is slower for modern hardware. |

## Documentation (add later, not at start)

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **API Docs** | utoipa | Generates OpenAPI from Rust types via derive macros. Better than paperclip. |
| **General docs** | Starlight (Astro) | Fast, accessible, built-in search. Write MDX, it handles the rest. |

---

## Cargo.toml Reference

```toml
[package]
name = "my-rust-app"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "server"
path = "src/main.rs"

[dependencies]
# Async runtime
tokio = { version = "1", features = ["full"] }

# HTTP framework
axum = { version = "0.7", features = ["macros"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["cors", "trace", "request-id", "compression-full"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Database
sqlx = { version = "0.8", features = ["runtime-tokio", "postgres", "uuid", "chrono", "migrate"] }

# Error handling
thiserror = "1"
anyhow = "1"

# Configuration
envy = "0.4"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }

# Utilities
uuid = { version = "1", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }
validator = { version = "0.18", features = ["derive"] }

[dev-dependencies]
tokio = { version = "1", features = ["full"] }
testcontainers = "0.15"
testcontainers-modules = { version = "0.3", features = ["postgres"] }

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
```

## Services

> See `shared/SERVICES.md` for detailed comparisons.

| Category | Primary | Notes |
|----------|---------|-------|
| **Hosting** | Railway | Or Fly.io for global VMs. Both support Rust Docker images. |
| **Database** | Supabase | Or self-hosted PostgreSQL. |
| **Cache** | Valkey | Redis fork, self-hosted. |
| **Observability** | Sentry + Grafana Cloud | Or self-hosted Prometheus + Jaeger. |

---

## Critical Notes

1. **`DATABASE_URL` at compile time**: SQLx macros verify queries at compile. Set `DATABASE_URL` in your environment or use `cargo sqlx prepare` for offline mode.
2. **Commit `.sqlx/`**: The offline query cache enables CI without a live database.
3. **`thiserror` over manual `impl Error`**: Always derive error implementations.
4. **No `.unwrap()` in handlers**: Return `AppError` instead — panics crash the whole server.
5. **Axum state must `Clone`**: `Arc<T>` for expensive resources, direct clone for cheap ones (PgPool is already Arc-based internally).
6. **Never block in async**: Wrap CPU-heavy work in `tokio::task::spawn_blocking`.
