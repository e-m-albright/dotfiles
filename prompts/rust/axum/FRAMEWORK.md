# Axum Framework

Ergonomic, composable web framework built on Tower. Type-safe extractors, no macros required.

---

## Quick Reference

```yaml
Framework:   Axum (github.com/tokio-rs/axum)
Middleware:  tower + tower-http
```

Axum is fully Tower-compatible — any Tower middleware works without modification.

---

## Project Structure

```
src/
├── main.rs              # Entry point: setup, wiring, server start
├── config.rs            # Environment configuration (envy)
├── error.rs             # AppError type + IntoResponse impl
├── state.rs             # AppState struct
├── router.rs            # Route registration
├── handler/             # HTTP handlers (one file per resource)
│   ├── mod.rs
│   ├── user.rs
│   └── health.rs
├── middleware/          # Custom Tower middleware
│   └── mod.rs
├── model/               # Domain types (serde, sqlx::FromRow)
│   └── user.rs
├── repository/          # Database access (sqlx)
│   └── user.rs
└── service/             # Business logic
    └── user.rs
migrations/              # SQLx migration files (YYYYMMDDHHMMSS_name.sql)
tests/
└── integration/         # Integration tests with testcontainers
.sqlx/                   # SQLx offline query cache (commit this)
```

---

## Application State

```rust
// src/state.rs
use sqlx::PgPool;
use std::sync::Arc;
use crate::config::Config;

#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,          // PgPool is Arc-based internally — cheap to clone
    pub config: Arc<Config>, // Wrap config in Arc to avoid cloning the whole struct
}
```

---

## Router

```rust
// src/router.rs
use axum::{routing::{delete, get, post, put}, Router};
use crate::{handler, state::AppState};

pub fn create(state: AppState) -> Router {
    Router::new()
        // Health
        .route("/health", get(handler::health::health))

        // Users
        .route("/api/v1/users", get(handler::user::list_users))
        .route("/api/v1/users", post(handler::user::create_user))
        .route("/api/v1/users/:id", get(handler::user::get_user))
        .route("/api/v1/users/:id", put(handler::user::update_user))
        .route("/api/v1/users/:id", delete(handler::user::delete_user))

        // Global middleware
        .layer(middleware_stack())
        .with_state(state)
}

fn middleware_stack() -> tower::ServiceBuilder<impl tower::Layer<axum::routing::Router>> {
    use tower_http::{
        compression::CompressionLayer,
        cors::CorsLayer,
        request_id::{MakeRequestUuid, PropagateRequestIdLayer, SetRequestIdLayer},
        trace::TraceLayer,
    };

    tower::ServiceBuilder::new()
        .layer(SetRequestIdLayer::x_request_id(MakeRequestUuid))
        .layer(TraceLayer::new_for_http())
        .layer(PropagateRequestIdLayer::x_request_id())
        .layer(CorsLayer::permissive()) // Tighten in production
        .layer(CompressionLayer::new())
}
```

---

## Handlers

```rust
// src/handler/user.rs
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::Deserialize;
use uuid::Uuid;

use crate::{error::AppError, model::user::{CreateUserRequest, UpdateUserRequest, User}, state::AppState};

// GET /api/v1/users
pub async fn list_users(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<User>>, AppError> {
    let limit = params.limit.unwrap_or(50).min(100) as i64;
    let offset = params.offset.unwrap_or(0) as i64;

    let users = state.db
        .find_all(limit, offset)
        .await
        .map_err(|e| AppError::Internal(anyhow::anyhow!(e)))?;

    Ok(Json(users))
}

// GET /api/v1/users/:id
pub async fn get_user(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<User>, AppError> {
    let user = sqlx::query_as!(
        User,
        "SELECT id, email, name, created_at, updated_at FROM users WHERE id = $1",
        id
    )
    .fetch_optional(&state.db)
    .await
    .map_err(|e| AppError::Internal(anyhow::anyhow!(e)))?
    .ok_or_else(|| AppError::NotFound(format!("user {id}")))?;

    Ok(Json(user))
}

// POST /api/v1/users
pub async fn create_user(
    State(state): State<AppState>,
    Json(req): Json<CreateUserRequest>,
) -> Result<(StatusCode, Json<User>), AppError> {
    // Validate
    if req.email.is_empty() {
        return Err(AppError::Validation("email is required".to_string()));
    }

    let user = sqlx::query_as!(
        User,
        "INSERT INTO users (email, name) VALUES ($1, $2)
         RETURNING id, email, name, created_at, updated_at",
        req.email,
        req.name,
    )
    .fetch_one(&state.db)
    .await
    .map_err(|e| match e {
        sqlx::Error::Database(ref db_err) if db_err.constraint() == Some("users_email_key") => {
            AppError::Conflict(format!("email {} already in use", req.email))
        }
        _ => AppError::Internal(anyhow::anyhow!(e)),
    })?;

    Ok((StatusCode::CREATED, Json(user)))
}

// DELETE /api/v1/users/:id
pub async fn delete_user(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<StatusCode, AppError> {
    let deleted = sqlx::query!("DELETE FROM users WHERE id = $1", id)
        .execute(&state.db)
        .await
        .map_err(|e| AppError::Internal(anyhow::anyhow!(e)))?
        .rows_affected()
        > 0;

    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError::NotFound(format!("user {id}")))
    }
}

#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub limit: Option<u32>,
    pub offset: Option<u32>,
}
```

---

## Health Handler

```rust
// src/handler/health.rs
use axum::{http::StatusCode, Json};
use serde_json::{json, Value};

pub async fn health() -> (StatusCode, Json<Value>) {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}
```

---

## Authentication Middleware

```rust
// src/middleware/auth.rs
use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
};

use crate::state::AppState;

pub async fn require_auth(
    State(state): State<AppState>,
    mut req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let token = req
        .headers()
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.strip_prefix("Bearer "))
        .ok_or(StatusCode::UNAUTHORIZED)?;

    let claims = verify_jwt(token, &state.config.jwt_secret)
        .map_err(|_| StatusCode::UNAUTHORIZED)?;

    req.extensions_mut().insert(claims);
    Ok(next.run(req).await)
}

// Add to a protected route group:
//
// use axum::middleware;
//
// Router::new()
//     .route("/me", get(handler::user::get_me))
//     .route_layer(middleware::from_fn_with_state(state.clone(), require_auth))
```

---

## Main Entry Point

```rust
// src/main.rs
use std::net::SocketAddr;
use anyhow::Result;
use sqlx::postgres::PgPoolOptions;

mod config;
mod error;
mod handler;
mod middleware;
mod model;
mod repository;
mod router;
mod service;
mod state;

use state::AppState;
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<()> {
    // Load config
    let config = config::Config::from_env()?;

    // Setup tracing
    setup_tracing(config.is_production());

    tracing::info!(env = %config.env, port = config.port, "starting server");

    // Connect to database
    let pool = PgPoolOptions::new()
        .max_connections(25)
        .min_connections(5)
        .connect(&config.database_url)
        .await?;

    // Run migrations
    sqlx::migrate!().run(&pool).await?;

    // Build app state
    let state = AppState {
        db: pool,
        config: Arc::new(config.clone()),
    };

    // Build router
    let app = router::create(state);

    // Bind and serve
    let addr = SocketAddr::from(([0, 0, 0, 0], config.port));
    tracing::info!(%addr, "listening");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}

fn setup_tracing(is_production: bool) {
    use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    let registry = tracing_subscriber::registry().with(filter);

    if is_production {
        registry.with(tracing_subscriber::fmt::layer().json()).init();
    } else {
        registry.with(tracing_subscriber::fmt::layer().pretty()).init();
    }
}

async fn shutdown_signal() {
    use tokio::signal;

    let ctrl_c = async {
        signal::ctrl_c().await.expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }

    tracing::info!("shutdown signal received");
}
```

---

## Testing Handlers

```rust
// tests/integration/user_test.rs
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use serde_json::json;
use tower::ServiceExt; // for .oneshot()

use crate::router;
use crate::state::AppState;

// Helper to build the app with a test database pool
async fn test_app() -> axum::Router {
    let pool = test_db_pool().await; // set up testcontainer
    let state = AppState {
        db: pool,
        config: Arc::new(test_config()),
    };
    router::create(state)
}

#[tokio::test]
async fn test_health_returns_ok() {
    let app = test_app().await;

    let response = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_create_user() {
    let app = test_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/users")
                .header("Content-Type", "application/json")
                .body(Body::from(json!({
                    "email": "test@example.com",
                    "name": "Test User"
                }).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
}

#[tokio::test]
async fn test_get_nonexistent_user_returns_404() {
    let app = test_app().await;
    let id = uuid::Uuid::new_v4();

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/api/v1/users/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
```

---

## Key Axum Concepts

### Extractors (in order, path before state)

```rust
// Path params
Path(id): Path<Uuid>

// Query string
Query(params): Query<MyParams>

// JSON body (consumes body, must be last)
Json(body): Json<MyRequest>

// App state (cheap clone — comes before body extractor)
State(state): State<AppState>

// Request extensions (set by middleware)
Extension(user): Extension<AuthClaims>
```

### Response Types

```rust
// Simple status
StatusCode::OK

// JSON response
Json(my_struct)

// Status + JSON
(StatusCode::CREATED, Json(my_struct))

// Error (implements IntoResponse)
AppError::NotFound("user".to_string())

// Custom headers
([(header::SET_COOKIE, cookie_value)], Json(body))
```

---

## Critical Rules (Axum)

### Always

- `AppState` must impl `Clone` — Axum clones it per request.
- Extractors that consume the body (`Json`, `Bytes`) must be the **last** extractor.
- Use `route_layer` not `layer` for per-route middleware (avoids running on 404s).
- Return `Result<_, AppError>` — never panic in handlers.

### Why Axum

- Type-safe extractors catch mismatches at compile time.
- Tower middleware ecosystem is extensive and composable.
- No magic macros — routes are just functions.
- Built and maintained by the Tokio team.
