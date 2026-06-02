# Chi Router

> chi/v5 patterns for Go HTTP services. Reach for chi over the stdlib mux when you
> want composable middleware, route groups, and URL-param helpers. For the broader
> Go stack and idioms, see [`../README.md`](../README.md).

## Quick reference

```yaml
Router:      chi/v5
Database:    sqlc + pgx/v5 + PostgreSQL
Migrations:  golang-migrate
Config:      envconfig
Logging:     slog (stdlib)
```

## Structure

```
cmd/server/main.go         — entry point, wire dependencies
internal/
  handler/                 — HTTP handlers (one file per resource)
  service/                 — business logic
  store/                   — sqlc-generated database code
  middleware/              — custom middleware
  model/                   — domain types
migrations/                — SQL migration files (.up.sql, .down.sql)
sqlc.yaml                  — sqlc configuration
```

## Patterns

- Mount routes in groups: `r.Route("/api/users", userHandler.Routes)`.
- Middleware chain order: logging → recovery → auth → rate limit.
- Use `chi.URLParam(r, "id")` for path parameters.
- Handler methods on a struct with dependencies injected via constructor.
- Return JSON with `render.JSON(w, r, response)` or `encoding/json`.

## Database (sqlc)

- Write SQL queries in `.sql` files with `-- name: GetUser :one` annotations.
- Run `sqlc generate` to produce type-safe Go code.
- Use `pgx/v5` connection pool via `pgxpool.New()`.

## Error handling

- Return structured JSON errors: `{"error": {"code": "NOT_FOUND", "message": "..."}}`.
- Use middleware to catch panics and log structured errors.

## Commands

```bash
just dev                   # Start with hot reload (air)
just build                 # Build binary
just test                  # Run tests
just db-migrate            # Run migrations
sqlc generate              # Regenerate database code
```

## See also

- [`../README.md`](../README.md) — Go stack selection, idioms, and code patterns
