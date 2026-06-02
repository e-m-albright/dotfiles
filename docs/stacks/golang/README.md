# Go

> Curated taste, not mandate — read this to derive per-project choices.

## Selection (pick / avoid / by phase)

Selection guidance is *what* to reach for; idioms and patterns below cover *how* to use them.

### Foundation — every project

| Category    | Pick               | Avoid           |
|-------------|--------------------|-----------------|
| Go version  | **1.25+**          | Older versions  |
| Linter      | **golangci-lint**  | Individual linters |
| Task runner | **Just**           | Make (arcane)   |
| Git hooks   | **Lefthook**       | Husky           |

### When needed

| Need             | Pick                                   | Avoid                                        |
|------------------|----------------------------------------|----------------------------------------------|
| HTTP router      | **stdlib `net/http`** (1.22+ method routing), then **chi/v5** when you want middleware/grouping | gin (heavier), stdlib mux for complex middleware (limited) |
| Database queries | **sqlc** (type-safe Go from SQL)       | GORM (magic, slow), raw SQL (no types)       |
| Postgres driver  | **pgx/v5**                             | lib/pq (unmaintained)                        |
| Migrations       | **golang-migrate**                     | goose (less ecosystem)                       |
| Config           | **envconfig**                          | viper (complex, YAML)                        |
| Logging          | **slog** (stdlib)                      | logrus (archived), zap (complex)             |
| HTTP client      | **stdlib `net/http`**                  | resty (unnecessary abstraction)              |
| Background jobs  | **River** (Postgres-backed, transactional enqueue) | asynq (needs Redis), hand-rolled cron |
| Server-rendered HTML | **templ** (type-safe templates) + HTMX | `html/template` (stringly-typed, runtime errors) |
| Testing          | **stdlib `testing` + testcontainers-go** (table-driven) | testify (assertions, not needed)   |
| Supply chain     | **govulncheck** (call-graph reachability) | see [security.md](../security.md) |

### At scale

| Need          | Pick                              | Notes                          |
|---------------|-----------------------------------|--------------------------------|
| Observability | **OpenTelemetry**                 | When 2+ services; OTLP export  |
| Docs          | **Starlight (Astro)** or **pkgsite** | Users vs. API audience      |

### Background jobs & server-rendered HTML

- **River** is the best-in-class Go job queue: Postgres-backed (no Redis dependency), transactional enqueue (jobs commit with your data — no dual-write race), cron/scheduled jobs, web UI. By the pgx author. Pick it over asynq unless you already run Redis and need its throughput profile. River is a *queue*, not durable execution — for crash-resumable multi-step workflows reach for Temporal/DBOS (see [services.md](../services.md#durable-execution--workflows)).
- **templ** compiles `.templ` files to type-checked Go (errors at compile time, not runtime). It's the canonical 2026 pairing with **HTMX** for server-rendered HTML without an SPA. Costs a `templ generate` codegen step in the build. Irrelevant if your Go services are pure JSON APIs.

### Don't install

- **GORM** — magic ORM; prefer sqlc for type-safe SQL.
- **viper** — envconfig is simpler for env-based config.
- **logrus** — archived; use slog (stdlib).
- **testify** — stdlib `testing` + table-driven tests suffice.

### Routing: stdlib vs. chi

Go 1.22+ added method + path-pattern routing and `r.PathValue`, so the stdlib mux
covers simple APIs without a dependency. Reach for **chi/v5** when you want
composable middleware chains, route groups, and `chi.URLParam`. Don't pull in
gin/chi reflexively for a handful of endpoints. See `frameworks/chi.md`.

## Idioms

- **stdlib-first** — prefer stdlib over third-party when reasonable.
- **slog** for structured logging (stdlib, Go 1.21+).
- **Error wrapping** — always wrap with context: `fmt.Errorf("context: %w", err)`.
- **Return errors, don't panic.** Panic is for unrecoverable programmer errors.
- **Handle every error** — no `_ = err`.
- Use `context.Context` as the first parameter for functions that do I/O.
- **Avoid `init()`** — prefer explicit initialization in `main()`.
- **No global mutable state.**
- **Avoid `interface{}`/`any`** — use generics or specific types.

### Naming

- Short, unexported names for local scope (`ctx`, `db`, `err`).
- Interfaces describe behavior: `Reader`, `Storer`, `UserService`.
- **Accept interfaces, return structs.**

### Formatting & deps

- **gofmt/goimports** for formatting — never override.
- **golangci-lint** for linting — don't introduce separate linters; don't ignore
  warnings without a documented reason.
- `go mod tidy` after dependency changes.
- Run `just check` (or `golangci-lint run`) before committing.

## Code patterns

### HTTP routing (stdlib, Go 1.22+)

```go
mux := http.NewServeMux()

// Method + path pattern
mux.HandleFunc("GET /users", h.ListUsers)
mux.HandleFunc("GET /users/{id}", h.GetUser)
mux.HandleFunc("POST /users", h.CreateUser)
mux.HandleFunc("PUT /users/{id}", h.UpdateUser)
mux.HandleFunc("DELETE /users/{id}", h.DeleteUser)

func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id") // path value extraction
    // ...
}
```

### slog logging

```go
import "log/slog"

logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

logger.Info("server starting", "port", 8080)
logger.Error("failed to connect", "error", err)
logger.With("request_id", reqID).Info("handling request")
```

### Error wrapping

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

### sqlc query definition

Write SQL in `.sql` files with `-- name:` annotations, then run `sqlc generate`
to produce type-safe Go.

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

### pgx connection pool

```go
import "github.com/jackc/pgx/v5/pgxpool"

config, _ := pgxpool.ParseConfig(databaseURL)
config.MaxConns = 25
config.MinConns = 5

pool, err := pgxpool.NewWithConfig(ctx, config)
```

### Testing

Use stdlib `testing` with `if got != want` style — no assertion libraries.

- **Table-driven tests** — the idiomatic pattern for multiple cases:

  ```go
  tests := []struct {
      name  string
      input string
      want  int
  }{
      {"empty", "", 0},
      {"single", "a", 1},
  }
  for _, tt := range tests {
      t.Run(tt.name, func(t *testing.T) {
          got := Len(tt.input)
          if got != tt.want {
              t.Errorf("Len(%q) = %d, want %d", tt.input, got, tt.want)
          }
      })
  }
  ```

- **`httptest`** for HTTP handler tests — `httptest.NewRecorder()` + `httptest.NewRequest()`:

  ```go
  func TestGetUser(t *testing.T) {
      mux := http.NewServeMux()
      h.RegisterRoutes(mux)

      req := httptest.NewRequest("GET", "/users/123", nil)
      rec := httptest.NewRecorder()

      mux.ServeHTTP(rec, req)

      if rec.Code != http.StatusOK {
          t.Errorf("expected 200, got %d", rec.Code)
      }
  }
  ```

- **`testcontainers-go`** for integration tests needing real databases.
- **`t.Helper()`** in test helpers so failures report the caller's line.
- **`t.Parallel()`** for independent tests — speeds up the suite.

### Common commands

```bash
go run ./cmd/server               # Run
go build -o bin/app ./cmd/server  # Build
go test ./...                     # Test
golangci-lint run                 # Lint
sqlc generate                     # Generate sqlc code
migrate up                        # Run migrations
```

## Project layout

```
cmd/server/main.go           # Entry point, wire dependencies
internal/                    # Private application code
├── config/config.go         # envconfig
├── handler/                 # HTTP handlers (one file per resource)
├── service/                 # Business logic
├── store/ (or repository/)  # Database access (sqlc-generated)
├── model/                   # Domain types
└── db/
    ├── migrations/          # SQL migrations (.up.sql, .down.sql)
    └── queries/             # sqlc SQL files
```

## See also

- [`frameworks/chi.md`](frameworks/chi.md) — chi/v5 router patterns
- [`../../engineering-philosophy.md`](../../engineering-philosophy.md) — universal code-health principles
