---
name: rust-axum-stack
description: |
  Implementation quick-reference for Rust Axum projects.
  Complements .ai/rules/ (rust.mdc, axum.mdc, stack-rust.mdc) with runnable code examples.
---

# Rust Axum Quick Reference

> For conventions and decisions, see `.ai/rules/rust.mdc` and `.ai/rules/axum.mdc`.
> This guide provides implementation patterns and working code examples.

## When This Applies

- Working with `.rs` files
- Axum HTTP handlers and routing
- SQLx database queries
- tracing/logging setup
- Error handling with thiserror/anyhow

## Critical Patterns

### Axum Handler Signature

```rust
// All extractors before body extractors; State before Json
pub async fn create_user(
    State(state): State<AppState>,
    Json(req): Json<CreateUserRequest>,
) -> Result<(StatusCode, Json<User>), AppError> {
    // ...
}
```

### AppError: typed errors + IntoResponse

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
        let (status, msg) = match &self {
            AppError::NotFound(m) => (StatusCode::NOT_FOUND, m.clone()),
            AppError::Validation(m) => (StatusCode::UNPROCESSABLE_ENTITY, m.clone()),
            AppError::Unauthorized => (StatusCode::UNAUTHORIZED, "unauthorized".into()),
            AppError::Internal(e) => {
                tracing::error!("internal: {e:?}");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".into())
            }
        };
        (status, Json(json!({ "error": msg }))).into_response()
    }
}
```

### SQLx Query

```rust
// Compile-time verified (requires DATABASE_URL at build time or .sqlx/ cache)
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

### tracing

```rust
use tracing::{info, error, instrument};

#[instrument(skip(pool), fields(user_id = %id))]
async fn fetch_user(pool: &PgPool, id: Uuid) -> Result<User, sqlx::Error> {
    info!("fetching user from db");
    // ...
}

// Structured fields
info!(port = config.port, env = %config.env, "server starting");
error!(error = ?err, "request failed");
```

### Configuration

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

### App Startup

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

## Commands

```bash
cargo run                          # Run
cargo watch -x run                 # Hot reload
cargo test                         # Test
cargo clippy -- -D warnings        # Lint
cargo fmt                          # Format
cargo sqlx prepare                 # Generate offline query cache
sqlx migrate run                   # Run migrations
sqlx migrate add <name>            # New migration
cargo audit                        # Security audit
```

## Common Mistakes to Avoid

1. **`.unwrap()` in handlers** — panics crash the server; always return `AppError`
2. **Body extractor not last** — `Json<T>` must be the last extractor argument
3. **Blocking in async** — use `tokio::task::spawn_blocking` for CPU work
4. **Mutex across `.await`** — deadlock risk; use `tokio::sync::Mutex` or restructure
5. **Not running `cargo sqlx prepare`** — CI will fail without the `.sqlx/` cache
6. **Missing `DATABASE_URL`** — SQLx macros need it at compile time

## File Structure

```
src/
├── main.rs          # Entry point
├── config.rs        # envy-based config
├── error.rs         # AppError + IntoResponse
├── state.rs         # AppState (Clone)
├── router.rs        # Route registration + middleware
├── handler/         # HTTP handlers (one file per resource)
├── model/           # Domain types (Serialize, FromRow)
├── repository/      # SQLx queries
└── service/         # Business logic
migrations/          # sqlx migration files
.sqlx/               # Offline query cache (commit this)
```
