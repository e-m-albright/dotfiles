# Chi Router

Lightweight, composable router that stays close to stdlib.

---

## Quick Reference

```yaml
Router:      Chi (github.com/go-chi/chi/v5)
```

Chi is fully net/http compatible — any stdlib middleware works without modification.

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
│   ├── routes.go          # Route registration
│   └── user.go            # User-related handlers
├── middleware/            # Custom middleware
│   └── auth.go
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

## HTTP Handler (Chi)

```go
package handler

import (
    "encoding/json"
    "log/slog"
    "net/http"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"

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

func (h *Handler) Routes() chi.Router {
    r := chi.NewRouter()

    // Global middleware
    r.Use(middleware.RequestID)
    r.Use(middleware.RealIP)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    // Health check
    r.Get("/health", h.Health)

    // API routes
    r.Route("/api/v1", func(r chi.Router) {
        r.Route("/users", func(r chi.Router) {
            r.Get("/", h.ListUsers)
            r.Post("/", h.CreateUser)

            r.Route("/{id}", func(r chi.Router) {
                r.Get("/", h.GetUser)
                r.Put("/", h.UpdateUser)
                r.Delete("/", h.DeleteUser)
            })
        })
    })

    return r
}

func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := chi.URLParam(r, "id")

    user, err := h.userSvc.GetByID(r.Context(), id)
    if err != nil {
        h.logger.Error("failed to get user", "id", id, "error", err)
        http.Error(w, "user not found", http.StatusNotFound)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}
```

---

## Route Groups with Middleware

```go
func (h *Handler) Routes() chi.Router {
    r := chi.NewRouter()

    // Public routes
    r.Group(func(r chi.Router) {
        r.Post("/login", h.Login)
        r.Post("/register", h.Register)
    })

    // Protected routes
    r.Group(func(r chi.Router) {
        r.Use(h.AuthMiddleware)

        r.Get("/me", h.GetCurrentUser)
        r.Put("/me", h.UpdateCurrentUser)

        // Admin-only routes
        r.Route("/admin", func(r chi.Router) {
            r.Use(h.AdminOnly)
            r.Get("/users", h.AdminListUsers)
            r.Delete("/users/{id}", h.AdminDeleteUser)
        })
    })

    return r
}
```

---

## Custom Middleware

```go
package handler

import (
    "context"
    "net/http"
    "strings"
)

type contextKey string

const userContextKey contextKey = "user"

func (h *Handler) AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
        if token == "" {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return
        }

        user, err := h.authSvc.ValidateToken(r.Context(), token)
        if err != nil {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return
        }

        ctx := context.WithValue(r.Context(), userContextKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func (h *Handler) AdminOnly(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user := r.Context().Value(userContextKey).(*model.User)
        if !user.IsAdmin {
            http.Error(w, "forbidden", http.StatusForbidden)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

---

## Main Entry Point

```go
package main

import (
    "context"
    "log/slog"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "myapp/internal/config"
    "myapp/internal/db"
    "myapp/internal/handler"
    "myapp/internal/repository"
    "myapp/internal/service"
)

func main() {
    // Load config
    cfg, err := config.Load()
    if err != nil {
        slog.Error("failed to load config", "error", err)
        os.Exit(1)
    }

    // Setup logger
    logger := setupLogger(cfg.Env)

    // Setup database
    ctx := context.Background()
    pool, err := db.NewPool(ctx, cfg.DatabaseURL)
    if err != nil {
        logger.Error("failed to connect to database", "error", err)
        os.Exit(1)
    }
    defer pool.Close()

    // Wire dependencies
    userRepo := repository.NewUserRepository(pool)
    userSvc := service.NewUserService(userRepo)
    h := handler.New(logger, userSvc)

    // Start server
    server := &http.Server{
        Addr:         ":" + cfg.Port,
        Handler:      h.Routes(),
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // Graceful shutdown
    go func() {
        logger.Info("server starting", "port", cfg.Port)
        if err := server.ListenAndServe(); err != http.ErrServerClosed {
            logger.Error("server error", "error", err)
        }
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    logger.Info("shutting down server...")
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(ctx); err != nil {
        logger.Error("server shutdown error", "error", err)
    }
}
```

---

## Testing

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
    router := h.Routes()

    // Create request
    req := httptest.NewRequest("GET", "/api/v1/users/123", nil)
    rec := httptest.NewRecorder()

    // Execute
    router.ServeHTTP(rec, req)

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

## Built-in Middleware

Chi includes useful middleware out of the box:

```go
import "github.com/go-chi/chi/v5/middleware"

r.Use(middleware.RequestID)     // X-Request-Id header
r.Use(middleware.RealIP)        // X-Forwarded-For handling
r.Use(middleware.Logger)        // Request logging
r.Use(middleware.Recoverer)     // Panic recovery
r.Use(middleware.Timeout(60 * time.Second))  // Request timeout
r.Use(middleware.Compress(5))   // Gzip compression
r.Use(middleware.Heartbeat("/ping"))  // Health endpoint
```

---

## Critical Rules (Chi)

### Always

- Use `chi.URLParam(r, "id")` for path parameters
- Use `r.Route()` for nested route groups
- Apply middleware at the appropriate scope (global vs route-specific)

### Why Chi over stdlib

- Composable subrouters and route groups
- Built-in middleware collection
- Cleaner middleware chaining
- Still fully net/http compatible
