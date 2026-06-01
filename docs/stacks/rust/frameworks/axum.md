# Axum

> Production HTTP APIs in Rust. Read with [../README.md](../README.md) for the underlying language taste.

## Stack

```yaml
Framework:   Axum 0.8+
Database:    SQLx + PostgreSQL (compile-time checked)
Migrations:  sqlx-cli
Async:       Tokio
Logging:     tracing + tracing-subscriber
```

## Patterns

- Extractors for request data: `Path`, `Query`, `Json`, `State`.
- Share state via `State<AppState>` (clonable; holds pool, config, services). `Arc` the config inside.
- Order extractors with `State` before body extractors — the body extractor (`Json<T>`) **must be last**.
- `impl IntoResponse` for custom error types — map variants to status codes.
- Routes: `Router::new().route("/users", get(list).post(create))`.
- Tower middleware: `ServiceBuilder::new().layer(...)`.
- Graceful shutdown: `tokio::signal::ctrl_c()` with `serve().with_graceful_shutdown()`.
- Use `?` in handlers — Axum calls `IntoResponse` on the `Err` arm.

### Handler signature

```rust
// All non-body extractors first; State before Json; body (Json) last.
pub async fn create_user(
    State(state): State<AppState>,
    Json(req): Json<CreateUserRequest>,
) -> Result<(StatusCode, Json<User>), AppError> {
    // ...
}
```

## Error handling

Define `AppError` with thiserror and implement `IntoResponse` to emit a standard envelope:
`{"error": {"code": "NOT_FOUND", "message": "..."}}`.

```rust
#[derive(Error, Debug)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("validation error: {0}")]
    Validation(String),
    #[error("unauthorized")]
    Unauthorized,
    #[error(transparent)]
    Internal(#[from] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, code, msg) = match &self {
            AppError::NotFound(m) => (StatusCode::NOT_FOUND, "NOT_FOUND", m.clone()),
            AppError::Validation(m) => (StatusCode::UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", m.clone()),
            AppError::Unauthorized => (StatusCode::UNAUTHORIZED, "UNAUTHORIZED", "unauthorized".into()),
            AppError::Internal(e) => {
                tracing::error!("internal: {e:?}");
                (StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "internal server error".into())
            }
        };
        (status, Json(json!({ "error": { "code": code, "message": msg } }))).into_response()
    }
}
```

## Database (SQLx)

- Compile-time checked queries via `sqlx::query_as!()`. Use `PgPool` from `sqlx::postgres`.
- Set `DATABASE_URL` in `.env` for compile-time checking; the macros need it at build time.
- Run `cargo sqlx prepare` to generate the offline `.sqlx/` query cache — **commit it** (CI fails without it).
- Migrations: `sqlx migrate add <name>`, `sqlx migrate run`.

```rust
let user = sqlx::query_as!(
    User,
    "SELECT id, email, name, created_at, updated_at FROM users WHERE id = $1",
    id
)
.fetch_optional(&state.db)
.await
.map_err(|e| AppError::Internal(anyhow::anyhow!(e)))?
.ok_or_else(|| AppError::NotFound(format!("user {id}")))?;
```

## App startup

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env()?;
    setup_tracing(config.is_production());

    let pool = PgPoolOptions::new()
        .max_connections(25)
        .connect(&config.database_url)
        .await?;

    sqlx::migrate!().run(&pool).await?;

    let state = AppState { db: pool, config: Arc::new(config.clone()) };
    let app = router::create(state);

    let listener = tokio::net::TcpListener::bind(("0.0.0.0", config.port)).await?;
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}
```

## SSE streaming

For chat interfaces and long-running operations:

```rust
use axum::response::sse::{Event, KeepAlive, Sse};
use futures::stream::Stream;

pub async fn chat(
    State(state): State<AppState>,
    Json(req): Json<ChatRequest>,
) -> Sse<impl Stream<Item = Result<Event, anyhow::Error>>> {
    let stream = async_stream::stream! {
        // yield Event::default().data("chunk") for each piece
        // yield Event::default().event("done").data("") to signal completion
    };
    Sse::new(stream).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("keep-alive"),
    )
}
```

- Use the `async_stream::stream!` macro for ergonomic stream construction.
- Always set `keep_alive` to prevent proxy/LB timeouts.
- Send structured JSON in `data` fields — parse on the client.
- Use named events (`.event("citation")`, `.event("chunk")`, `.event("done")`) to distinguish message types.

## Bulk data processing

For handlers that trigger heavy computation:

- Offload CPU work: `tokio::task::spawn_blocking(move || parse_csv(&path))`.
- Rate-limit outbound API calls: `Arc<Semaphore>` in `AppState`, `let permit = semaphore.acquire().await?`.
- Stream large responses instead of buffering — `axum::body::Body::from_stream()`.

## File structure

```
src/
├── main.rs          # Entry point, router, server setup
├── config.rs        # envy-based config
├── error.rs         # AppError + IntoResponse
├── state.rs         # AppState (Clone)
├── router.rs        # Route registration + middleware
├── handler/         # HTTP handlers (one file per resource)
├── model/           # Domain types (Serialize, FromRow)
├── repository/      # SQLx queries
├── service/         # Business logic
└── middleware/      # tower middleware layers
migrations/          # sqlx migration files
.sqlx/               # Offline query cache (commit this)
```

## Commands

```bash
cargo run                          # Run
cargo watch -x run                 # Hot reload (or `just dev`)
cargo test                         # Test
cargo clippy -- -D warnings        # Lint
cargo fmt                          # Format
cargo sqlx prepare                 # Generate offline query cache
sqlx migrate add <name>            # New migration
sqlx migrate run                   # Run migrations
cargo audit                        # Security audit
```

## Common mistakes

1. **`.unwrap()` in handlers** — panics crash the server; always return `AppError`.
2. **Body extractor not last** — `Json<T>` must be the final extractor argument.
3. **Blocking in async** — use `tokio::task::spawn_blocking` for CPU work.
4. **Mutex across `.await`** — deadlock risk; use `tokio::sync::Mutex` or restructure.
5. **Not running `cargo sqlx prepare`** — CI fails without the `.sqlx/` cache.
6. **Missing `DATABASE_URL`** — SQLx macros need it at compile time.
