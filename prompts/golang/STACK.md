# Golang Stack

**Philosophy**: Simple, performant, reliable services with minimal dependencies.

## Runtime & Tooling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Go Version** | 1.22+ | Latest stable with rangefunc, improved stdlib. |
| **Module System** | Go Modules | Standard, no alternatives needed. |
| **Linter** | golangci-lint | Combines 100+ linters, fast, configurable. |
| **Formatter** | gofmt/goimports | Built-in, standard. No bikeshedding. |
| **Task Runner** | Just | Makefiles work but Just is more readable. |

## Framework Philosophy

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **HTTP Router** | stdlib (net/http) | Go 1.22+ has route patterns. Chi/Gin add complexity without benefit for most apps. |
| **Alternative Router** | Chi | If you need middleware chaining, Chi is minimal and stdlib-compatible. |

> **Note**: The Go community favors stdlib over frameworks. Use external packages only when stdlib is insufficient.

## Database & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **SQL Generation** | sqlc | ORMs hide SQL; raw SQL is error-prone. sqlc generates type-safe Go from SQL. |
| **Migrations** | golang-migrate | Widely used, supports embed, works with sqlc. |
| **Database** | PostgreSQL | Industry standard for production workloads. |
| **Driver** | pgx/v5 | Fastest Postgres driver, native connection pooling. |
| **Connection Pool** | pgxpool | Built into pgx, no separate package needed. |

## Configuration & Environment

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Config** | envconfig | Viper is heavy. envconfig is simple, struct-based. |
| **Logging** | slog | Built-in since Go 1.21. No need for zerolog/zap anymore. |
| **Errors** | stdlib errors | cockroachdb/errors is good but stdlib is sufficient for most apps. |

## HTTP & APIs

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **HTTP Client** | stdlib net/http | Sufficient for most needs. resty adds abstraction. |
| **JSON** | encoding/json | Standard. Use jsoniter only if profiling shows need. |
| **Validation** | go-playground/validator | De facto standard, struct tags, comprehensive. |
| **OpenAPI** | ogen | Generates server/client from OpenAPI spec. Better than oapi-codegen. |

## Testing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | stdlib testing | Built-in, sufficient. Testify adds unnecessary deps. |
| **Assertions** | stdlib + is | Minimal assertion library if needed. Or just use if/t.Errorf. |
| **Mocking** | gomock | Standard for interface mocking. |
| **HTTP Testing** | httptest | Built-in, excellent for handler testing. |
| **Integration** | testcontainers-go | Real databases in tests via Docker. |

## Concurrency & Background Jobs

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Workers** | errgroup | stdlib (golang.org/x/sync/errgroup), handles errors properly. |
| **Job Queue** | River | Postgres-based, no Redis needed. Modern, type-safe. |
| **Scheduling** | robfig/cron | De facto standard for cron scheduling. |

## Observability

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Logging** | slog | Built-in since 1.21. Structured, fast, standard. |
| **Metrics** | prometheus/client_golang | Industry standard for Go services. |
| **Tracing** | OpenTelemetry | Vendor-neutral, industry standard. |

## Development

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Hot Reload** | air | Fast, reliable file watcher for Go. |
| **API Docs** | swaggo/swag | Generates OpenAPI from code comments. |

---

## Version Requirements

```go
// go.mod
go 1.22

require (
    github.com/jackc/pgx/v5 v5.7.0
    github.com/sqlc-dev/sqlc v1.27.0
    github.com/kelseyhightower/envconfig v1.4.0
    github.com/go-playground/validator/v10 v10.23.0
)
```

## Services

> See `shared/SERVICES.md` for detailed comparisons.

| Category | Primary | Notes |
|----------|---------|-------|
| **Hosting** | Railway | Or Fly.io for global VMs. |
| **Database** | Supabase | Or self-hosted Postgres. |
| **Cache** | Valkey | Redis fork, self-hosted. |
| **Observability** | Sentry + Grafana Cloud | Or self-hosted Prometheus + Jaeger. |

---

## Critical Notes

1. **Go 1.22+ routing**: Use `http.HandleFunc("GET /users/{id}", handler)` — no need for Chi/Gin
2. **slog over zerolog/zap**: Built-in since 1.21, use it unless you have specific needs
3. **sqlc over GORM**: Generate type-safe code from SQL, don't hide SQL behind an ORM
4. **Interface small**: Define interfaces where they're used, not where implemented
5. **Error wrapping**: Use `fmt.Errorf("context: %w", err)` for stack traces
