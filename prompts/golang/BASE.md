# AGENTS.md — Golang (Base)

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Go 1.22+
Database:    sqlc + pgx/v5 + PostgreSQL
Config:      envconfig
Logging:     slog (stdlib)
Testing:     stdlib testing + testcontainers
Linting:     golangci-lint
Tasks:       Just
```

---

## Commands (Shared)

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

## Service Layer

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

---

## sqlc Query

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

---

## Configuration

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

---

## Logging with slog

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

---

## Error Handling

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

---

## Database Connection

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
5. **Architecture decisions** — Go in `.architecture/adr/`, not `.agents/`

---

## Critical Rules

### Always

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
