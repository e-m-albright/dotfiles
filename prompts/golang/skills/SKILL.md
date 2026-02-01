---
name: golang-stdlib-stack
description: |
  Use this skill when working with Go 1.22+ projects.
  Covers: stdlib HTTP routing, sqlc, pgx, slog logging, error handling.
---

# Go stdlib Stack

## When This Skill Applies

- Working with `.go` files
- HTTP handlers and routing
- Database operations with sqlc/pgx
- Configuration and logging
- Testing Go code

## Critical Patterns

### Go 1.22+ HTTP Routing

```go
// New routing syntax (Go 1.22+)
mux := http.NewServeMux()

// Method + path pattern
mux.HandleFunc("GET /users", h.ListUsers)
mux.HandleFunc("GET /users/{id}", h.GetUser)
mux.HandleFunc("POST /users", h.CreateUser)
mux.HandleFunc("PUT /users/{id}", h.UpdateUser)
mux.HandleFunc("DELETE /users/{id}", h.DeleteUser)

// Access path values
func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")  // Go 1.22+ path value extraction
    // ...
}
```

### slog Logging (Go 1.21+)

```go
import "log/slog"

// Setup
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

// Usage
logger.Info("server starting", "port", 8080)
logger.Error("failed to connect", "error", err)
logger.With("request_id", reqID).Info("handling request")
```

### Error Wrapping

```go
// Wrap errors with context
if err != nil {
    return fmt.Errorf("get user by id %s: %w", id, err)
}

// Check wrapped errors
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrNotFound
}
```

### sqlc Query Definition

```sql
-- name: GetUserByID :one
SELECT id, email, name, created_at
FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT id, email, name, created_at
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: CreateUser :one
INSERT INTO users (email, name)
VALUES ($1, $2)
RETURNING *;
```

### pgx Connection Pool

```go
import "github.com/jackc/pgx/v5/pgxpool"

config, _ := pgxpool.ParseConfig(databaseURL)
config.MaxConns = 25
config.MinConns = 5

pool, err := pgxpool.NewWithConfig(ctx, config)
```

### Handler Testing

```go
func TestGetUser(t *testing.T) {
    // Setup
    mux := http.NewServeMux()
    h.RegisterRoutes(mux)

    // Request
    req := httptest.NewRequest("GET", "/users/123", nil)
    rec := httptest.NewRecorder()

    // Execute
    mux.ServeHTTP(rec, req)

    // Assert
    if rec.Code != http.StatusOK {
        t.Errorf("expected 200, got %d", rec.Code)
    }
}
```

## Commands

```bash
go run ./cmd/server         # Run
go build -o bin/app ./cmd/server  # Build
go test ./...               # Test
golangci-lint run           # Lint
sqlc generate               # Generate sqlc
migrate up                  # Run migrations
```

## Common Mistakes to Avoid

1. **Using Gin/Chi for simple APIs** — Go 1.22+ stdlib is sufficient
2. **Using zerolog/zap** — slog is built-in since Go 1.21
3. **Using GORM** — sqlc generates type-safe code from SQL
4. **Ignoring errors** — Always check and handle errors
5. **Using `interface{}`** — Use generics or specific types

## File Structure

```
cmd/server/main.go           # Entry point
internal/
├── config/config.go         # envconfig
├── handler/                  # HTTP handlers
├── service/                  # Business logic
├── repository/               # Database access (sqlc generated)
└── db/
    ├── migrations/           # SQL migrations
    └── queries/              # sqlc SQL files
```
