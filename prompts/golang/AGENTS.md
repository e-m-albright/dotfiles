# AGENTS.md — Golang

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Go 1.22+
Router:      stdlib net/http (Go 1.22 patterns)
Database:    sqlc + pgx/v5 + PostgreSQL
Config:      envconfig
Logging:     slog (stdlib)
Testing:     stdlib testing + testcontainers
Linting:     golangci-lint
Tasks:       Just
```

---

## Commands

```bash
# Development
just dev                   # Start with hot reload (air)
just build                 # Build binary
just run                   # Run binary

# Quality
just check                 # Run all checks (lint, test)
just lint                  # golangci-lint
just fmt                   # gofmt + goimports

# Testing
just test                  # Run tests
just test-v                # Verbose tests
just test-cov              # Tests with coverage

# Database
just db-migrate            # Run migrations
just db-new name           # Create new migration
just sqlc                  # Generate sqlc code

# Dependencies
just mod                   # go mod tidy
just update                # Update dependencies
```

---

## Project Structure

```
cmd/
├── server/
│   └── main.go            # Application entry point
internal/
├── config/
│   └── config.go          # Environment configuration
├── handler/               # HTTP handlers
│   ├── handler.go         # Handler struct + constructor
│   └── user.go            # User-related handlers
├── service/               # Business logic
│   └── user.go
├── repository/            # Database access
│   └── user.go
├── model/                 # Domain types
│   └── user.go
└── db/
    ├── migrations/        # SQL migrations
    ├── queries/           # sqlc SQL files
    └── sqlc.yaml          # sqlc configuration
pkg/                       # Shared packages (if any)
tests/
└── integration/           # Integration tests
```

---

## Patterns

### HTTP Handler (Go 1.22+)

```go
package handler

import (
    "encoding/json"
    "log/slog"
    "net/http"

    "myapp/internal/service"
)

type Handler struct {
    logger  *slog.Logger
    userSvc *service.UserService
}

func New(logger *slog.Logger, userSvc *service.UserService) *Handler {
    return &Handler{
        logger:  logger,
        userSvc: userSvc,
    }
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
    // Go 1.22+ pattern routing
    mux.HandleFunc("GET /users", h.ListUsers)
    mux.HandleFunc("GET /users/{id}", h.GetUser)
    mux.HandleFunc("POST /users", h.CreateUser)
    mux.HandleFunc("PUT /users/{id}", h.UpdateUser)
    mux.HandleFunc("DELETE /users/{id}", h.DeleteUser)
}

func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id") // Go 1.22+ path values

    user, err := h.userSvc.GetByID(r.Context(), id)
    if err != nil {
        h.logger.Error("failed to get user", "id", id, "error", err)
        http.Error(w, "user not found", http.StatusNotFound)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}
```

### Service Layer

```go
package service

import (
    "context"
    "fmt"

    "myapp/internal/model"
    "myapp/internal/repository"
)

type UserService struct {
    repo *repository.UserRepository
}

func NewUserService(repo *repository.UserRepository) *UserService {
    return &UserService{repo: repo}
}

func (s *UserService) GetByID(ctx context.Context, id string) (*model.User, error) {
    user, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("get user by id: %w", err)
    }
    return user, nil
}

func (s *UserService) Create(ctx context.Context, input model.CreateUserInput) (*model.User, error) {
    // Validate
    if input.Email == "" {
        return nil, fmt.Errorf("email is required")
    }

    // Create
    user, err := s.repo.Create(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("create user: %w", err)
    }

    return user, nil
}
```

### sqlc Query

```sql
-- internal/db/queries/user.sql

-- name: GetUserByID :one
SELECT id, email, name, created_at, updated_at
FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT id, email, name, created_at, updated_at
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: CreateUser :one
INSERT INTO users (email, name)
VALUES ($1, $2)
RETURNING id, email, name, created_at, updated_at;

-- name: UpdateUser :one
UPDATE users
SET email = $2, name = $3, updated_at = NOW()
WHERE id = $1
RETURNING id, email, name, created_at, updated_at;

-- name: DeleteUser :exec
DELETE FROM users WHERE id = $1;
```

### Configuration

```go
package config

import (
    "fmt"

    "github.com/kelseyhightower/envconfig"
)

type Config struct {
    // Server
    Port string `envconfig:"PORT" default:"8080"`
    Env  string `envconfig:"ENV" default:"development"`

    // Database
    DatabaseURL string `envconfig:"DATABASE_URL" required:"true"`

    // Auth
    JWTSecret string `envconfig:"JWT_SECRET" required:"true"`
}

func Load() (*Config, error) {
    var cfg Config
    if err := envconfig.Process("", &cfg); err != nil {
        return nil, fmt.Errorf("load config: %w", err)
    }
    return &cfg, nil
}
```

### Logging with slog

```go
package main

import (
    "log/slog"
    "os"
)

func setupLogger(env string) *slog.Logger {
    var handler slog.Handler

    if env == "production" {
        // JSON for production (structured, machine-readable)
        handler = slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
            Level: slog.LevelInfo,
        })
    } else {
        // Text for development (human-readable)
        handler = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
            Level: slog.LevelDebug,
        })
    }

    return slog.New(handler)
}

// Usage
logger.Info("server starting", "port", cfg.Port)
logger.Error("failed to connect", "error", err)
logger.With("request_id", reqID).Info("handling request")
```

### Error Handling

```go
package apperror

import "fmt"

type AppError struct {
    Code    string
    Message string
    Err     error
}

func (e *AppError) Error() string {
    if e.Err != nil {
        return fmt.Sprintf("%s: %v", e.Message, e.Err)
    }
    return e.Message
}

func (e *AppError) Unwrap() error {
    return e.Err
}

// Common errors
func NotFound(resource string) *AppError {
    return &AppError{
        Code:    "NOT_FOUND",
        Message: fmt.Sprintf("%s not found", resource),
    }
}

func Validation(message string) *AppError {
    return &AppError{
        Code:    "VALIDATION_ERROR",
        Message: message,
    }
}

func Internal(err error) *AppError {
    return &AppError{
        Code:    "INTERNAL_ERROR",
        Message: "internal server error",
        Err:     err,
    }
}
```

### Database Connection

```go
package db

import (
    "context"
    "fmt"

    "github.com/jackc/pgx/v5/pgxpool"
)

func NewPool(ctx context.Context, databaseURL string) (*pgxpool.Pool, error) {
    config, err := pgxpool.ParseConfig(databaseURL)
    if err != nil {
        return nil, fmt.Errorf("parse database url: %w", err)
    }

    // Connection pool settings
    config.MaxConns = 25
    config.MinConns = 5

    pool, err := pgxpool.NewWithConfig(ctx, config)
    if err != nil {
        return nil, fmt.Errorf("create pool: %w", err)
    }

    // Verify connection
    if err := pool.Ping(ctx); err != nil {
        return nil, fmt.Errorf("ping database: %w", err)
    }

    return pool, nil
}
```

### Testing

```go
package handler_test

import (
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    "myapp/internal/handler"
    "myapp/internal/model"
)

func TestGetUser(t *testing.T) {
    // Setup
    h := handler.New(mockLogger, mockUserSvc)
    mux := http.NewServeMux()
    h.RegisterRoutes(mux)

    // Create request
    req := httptest.NewRequest("GET", "/users/123", nil)
    rec := httptest.NewRecorder()

    // Execute
    mux.ServeHTTP(rec, req)

    // Assert
    if rec.Code != http.StatusOK {
        t.Errorf("expected status 200, got %d", rec.Code)
    }

    var user model.User
    if err := json.NewDecoder(rec.Body).Decode(&user); err != nil {
        t.Fatalf("failed to decode response: %v", err)
    }

    if user.ID != "123" {
        t.Errorf("expected user ID 123, got %s", user.ID)
    }
}
```

---

## File Naming

| Type | Convention | Example |
|------|------------|---------|
| Packages | lowercase | `handler`, `service`, `repository` |
| Files | snake_case | `user_handler.go`, `db_pool.go` |
| Types | PascalCase | `type UserService struct`, `type Config struct` |
| Functions | PascalCase (exported), camelCase (unexported) | `GetByID()`, `parseConfig()` |
| Constants | PascalCase or ALL_CAPS | `MaxRetries`, `DEFAULT_TIMEOUT` |
| Interfaces | -er suffix | `Reader`, `Writer`, `UserRepository` |

---

## Git Conventions

### Commit Messages

```
type(scope): description

feat(api): add user registration endpoint
fix(db): handle connection timeout gracefully
refactor(handler): extract validation logic
test(service): add user creation tests
docs(readme): update installation steps
chore(deps): bump pgx to v5.7.0
```

---

## Agent Output Rules

1. **All artifacts go in `.agents/`** — Never create random files in project root
2. **Date-prefix plans** — `YYYY-MM-DD-feature-name.md`
3. **Update .agents/README.md** — Keep index of all agent-generated files
4. **Clean working files** — Delete when no longer needed
5. **Architecture decisions** — Go in `.decisions/adr/`, not `.agents/`

---

## Critical Rules

### Always

- Use Go 1.22+ HTTP routing patterns (`GET /users/{id}`)
- Use `context.Context` for cancellation and timeouts
- Use `slog` for logging (stdlib, Go 1.21+)
- Use `fmt.Errorf("context: %w", err)` for error wrapping
- Run `go mod tidy` after adding/removing imports

### Never

- Use `panic` for expected errors — return errors instead
- Use global variables for state — pass dependencies explicitly
- Ignore errors — always check and handle them
- Use `init()` for complex logic — keep it for simple registrations
- Use `interface{}` — use generics or specific types

### Ask First

- Adding new dependencies
- Changing database schema
- Modifying API contracts
- Deleting files
