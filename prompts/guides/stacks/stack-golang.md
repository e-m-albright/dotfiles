# Go Stack Decisions

## Phase 1 — Every Project

| Category | Pick | Avoid |
|----------|------|-------|
| Go version | **1.25+** | Older versions |
| Linter | **golangci-lint** | Individual linters |
| Task runner | **Just** | Make (arcane) |
| Git hooks | **Lefthook** | Husky |

## Phase 2 — When Needed

| Need | Pick | Avoid |
|------|------|-------|
| HTTP router | **chi/v5** | gin (heavier), stdlib mux (limited) |
| Database queries | **sqlc** | GORM (magic, slow), raw SQL (no types) |
| Postgres driver | **pgx/v5** | lib/pq (unmaintained) |
| Migrations | **golang-migrate** | goose (less ecosystem) |
| Config | **envconfig** | viper (complex, YAML) |
| Logging | **slog** (stdlib) | logrus (archived), zap (complex) |
| HTTP client | **stdlib net/http** | resty (unnecessary abstraction) |
| Testing | **stdlib testing + testcontainers** | testify (assertions, not needed) |

## Phase 3 — At Scale

| Need | Pick | Notes |
|------|------|-------|
| Observability | **OpenTelemetry** | When 2+ services |
| Docs | **Starlight (Astro)** or **pkgsite** | Depends on audience |

## What NOT to Install

| Tool | Why Skip |
|------|----------|
| GORM | Magic ORM, prefer sqlc for type-safe SQL |
| viper | envconfig is simpler for env-based config |
| logrus | Archived — use slog (stdlib) |
| testify | stdlib `testing` + table-driven tests is enough |
