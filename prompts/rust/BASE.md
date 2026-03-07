# AGENTS.md — Rust (Base)

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Language:    Rust (stable)
Async:       Tokio
Database:    SQLx + PostgreSQL
Config:      envy (env vars -> struct via serde)
Logging:     tracing + tracing-subscriber
Errors:      thiserror (domain) + anyhow (application)
Testing:     built-in + testcontainers-rs
Linting:     clippy
Formatter:   rustfmt
Git Hooks:   Lefthook (parallel, YAML config)
Tasks:       Just
```

---

## Commands (Shared)

```bash
# Development
just dev                   # Run with hot reload (cargo-watch)
just build                 # cargo build
just run                   # cargo run

# Quality
just check                 # Run all checks (fmt, clippy, test)
just clippy                # cargo clippy -- -D warnings
just fmt                   # cargo fmt
just fmt-check             # cargo fmt -- --check

# Testing
just test                  # cargo test
just test-v                # cargo test -- --nocapture
just test-cov              # Coverage report (cargo-llvm-cov)

# Database
just db-migrate            # sqlx migrate run
just db-rollback           # sqlx migrate revert
just db-new name           # sqlx migrate add <name>

# Dependencies
just update                # cargo update
just audit                 # cargo audit
```

---

## Error Handling

Rust error handling follows two distinct roles:

1. **Domain errors** (typed, matchable): use `thiserror`
2. **Application propagation** (handlers, main): use `anyhow`

### Domain Errors with thiserror

```rust
// src/error.rs
use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),

    #[error("validation error: {0}")]
    Validation(String),

    #[error("unauthorized")]
    Unauthorized,

    #[error("conflict: {0}")]
    Conflict(String),

    #[error(transparent)]
    Internal(#[from] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            AppError::Validation(msg) => (StatusCode::UNPROCESSABLE_ENTITY, msg.clone()),
            AppError::Unauthorized => (StatusCode::UNAUTHORIZED, "unauthorized".to_string()),
            AppError::Conflict(msg) => (StatusCode::CONFLICT, msg.clone()),
            AppError::Internal(err) => {
                tracing::error!("internal error: {err:?}");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".to_string())
            }
        };

        (status, Json(json!({ "error": message }))).into_response()
    }
}

// Convert SQLx errors to AppError
impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        match err {
            sqlx::Error::RowNotFound => AppError::NotFound("record".to_string()),
            _ => AppError::Internal(anyhow::anyhow!(err)),
        }
    }
}
```

### Service-Level Errors

```rust
// src/service/user.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UserError {
    #[error("user with email {0} already exists")]
    EmailConflict(String),

    #[error("user {0} not found")]
    NotFound(String),

    #[error(transparent)]
    Database(#[from] sqlx::Error),
}

// Convert to AppError at the handler boundary
impl From<UserError> for AppError {
    fn from(err: UserError) -> Self {
        match err {
            UserError::EmailConflict(email) => AppError::Conflict(format!("email {email} in use")),
            UserError::NotFound(id) => AppError::NotFound(format!("user {id}")),
            UserError::Database(e) => AppError::Internal(anyhow::anyhow!(e)),
        }
    }
}
```

---

## Configuration

Use `envy` to deserialize environment variables into a struct via serde.

```rust
// src/config.rs
use serde::Deserialize;
use anyhow::Result;

#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    // Application
    #[serde(default = "default_port")]
    pub port: u16,
    #[serde(default = "default_env")]
    pub env: String,

    // Database
    pub database_url: String,

    // Auth
    pub jwt_secret: String,
    #[serde(default = "default_jwt_expiry")]
    pub jwt_expiry_hours: u64,
}

fn default_port() -> u16 { 3000 }
fn default_env() -> String { "development".to_string() }
fn default_jwt_expiry() -> u64 { 24 }

impl Config {
    pub fn from_env() -> Result<Self> {
        envy::from_env::<Config>()
            .map_err(|e| anyhow::anyhow!("failed to load config: {e}"))
    }

    pub fn is_production(&self) -> bool {
        self.env == "production"
    }
}
```

---

## Logging with tracing

```rust
// src/main.rs — setup
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

fn setup_tracing(is_production: bool) {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    let registry = tracing_subscriber::registry().with(filter);

    if is_production {
        // JSON for production (structured, machine-readable)
        registry
            .with(tracing_subscriber::fmt::layer().json())
            .init();
    } else {
        // Pretty output for development
        registry
            .with(tracing_subscriber::fmt::layer().pretty())
            .init();
    }
}

// Usage throughout the codebase
use tracing::{info, error, warn, debug, instrument};

#[instrument(skip(pool), fields(user_id = %id))]
async fn get_user(pool: &PgPool, id: Uuid) -> Result<User, UserError> {
    info!("fetching user");
    // ...
}

// Structured logging
info!(port = config.port, env = %config.env, "server starting");
error!(error = ?err, request_id = %req_id, "request failed");
```

---

## Database with SQLx

```rust
// src/repository/user.rs
use sqlx::PgPool;
use uuid::Uuid;
use anyhow::Result;

use crate::model::user::{User, CreateUserInput};

pub struct UserRepository {
    pool: PgPool,
}

impl UserRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    pub async fn find_by_id(&self, id: Uuid) -> Result<Option<User>, sqlx::Error> {
        sqlx::query_as!(
            User,
            "SELECT id, email, name, created_at, updated_at FROM users WHERE id = $1",
            id
        )
        .fetch_optional(&self.pool)
        .await
    }

    pub async fn find_all(&self, limit: i64, offset: i64) -> Result<Vec<User>, sqlx::Error> {
        sqlx::query_as!(
            User,
            "SELECT id, email, name, created_at, updated_at
             FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset
        )
        .fetch_all(&self.pool)
        .await
    }

    pub async fn create(&self, input: CreateUserInput) -> Result<User, sqlx::Error> {
        sqlx::query_as!(
            User,
            "INSERT INTO users (email, name) VALUES ($1, $2)
             RETURNING id, email, name, created_at, updated_at",
            input.email,
            input.name,
        )
        .fetch_one(&self.pool)
        .await
    }

    pub async fn delete(&self, id: Uuid) -> Result<bool, sqlx::Error> {
        let result = sqlx::query!("DELETE FROM users WHERE id = $1", id)
            .execute(&self.pool)
            .await?;
        Ok(result.rows_affected() > 0)
    }
}
```

### SQLx Setup Notes

```bash
# Required: set DATABASE_URL before running cargo build (for compile-time checks)
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/myapp"

# Run migrations at startup
sqlx::migrate!().run(&pool).await?;

# Generate offline query cache for CI (commit .sqlx/ directory)
cargo sqlx prepare

# Create a new migration
sqlx migrate add create_users_table

# Run migrations manually
sqlx migrate run
```

---

## Domain Models

```rust
// src/model/user.rs
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct User {
    pub id: Uuid,
    pub email: String,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct CreateUserInput {
    pub email: String,
    pub name: String,
}

#[derive(Debug, Deserialize)]
pub struct UpdateUserInput {
    pub email: Option<String>,
    pub name: Option<String>,
}
```

---

## Testing

```rust
// Unit test (within same file)
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        // Test pure functions without I/O
    }

    #[tokio::test]
    async fn test_async_function() {
        // Async unit test
    }
}

// Integration test (tests/integration/user_test.rs)
use testcontainers::{clients::Cli, images::postgres::Postgres};
use sqlx::PgPool;

#[tokio::test]
async fn test_create_user() {
    let docker = Cli::default();
    let pg = docker.run(Postgres::default());
    let url = format!(
        "postgres://postgres:postgres@127.0.0.1:{}/postgres",
        pg.get_host_port_ipv4(5432)
    );

    let pool = PgPool::connect(&url).await.unwrap();
    sqlx::migrate!().run(&pool).await.unwrap();

    let repo = UserRepository::new(pool);
    let user = repo.create(CreateUserInput {
        email: "test@example.com".to_string(),
        name: "Test User".to_string(),
    }).await.unwrap();

    assert_eq!(user.email, "test@example.com");
}
```

---

## File Naming

| Type | Convention | Example |
|------|------------|---------|
| Files / modules | snake_case | `user_handler.rs`, `db_pool.rs` |
| Structs / Enums | PascalCase | `struct UserService`, `enum AppError` |
| Traits | PascalCase | `trait UserRepository` |
| Functions / methods | snake_case | `fn get_by_id()`, `fn parse_config()` |
| Constants | SCREAMING_SNAKE_CASE | `const MAX_CONNECTIONS: u32 = 25;` |
| Type aliases | PascalCase | `type Result<T> = std::result::Result<T, AppError>` |

---

## Stack Reference

See the Rust STACK.md for full technology choices and rationale.
