# Shared Infrastructure

These patterns apply across all recipes when you need containerization or infrastructure-as-code.

> **Note**: Don't add infrastructure until you need it. A local dev project doesn't need Docker.
> A side project doesn't need Pulumi. Add these when deploying to production.

---

## Containerization

### Docker Philosophy

- **Multi-stage builds**: Keep production images small
- **Non-root users**: Security best practice
- **Layer caching**: Order commands for fast rebuilds
- **.dockerignore**: Don't copy node_modules, .git, etc.

### Python Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=app:app src/ ./src/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### TypeScript/Bun Dockerfile

```dockerfile
# Build stage
FROM oven/bun:1 as builder

WORKDIR /app

# Copy dependency files
COPY package.json bun.lockb ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source and build
COPY . .
RUN bun run build

# Runtime stage
FROM oven/bun:1-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 app

# Copy built application
COPY --from=builder --chown=app:app /app/build ./build
COPY --from=builder --chown=app:app /app/package.json ./

USER app

EXPOSE 3000

CMD ["bun", "./build/index.js"]
```

### Go Dockerfile

```dockerfile
# Build stage
FROM golang:1.22-alpine as builder

WORKDIR /app

# Copy dependency files
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server ./cmd/server

# Runtime stage
FROM alpine:3.19

WORKDIR /app

# Create non-root user
RUN adduser -D -u 1000 app

# Copy binary
COPY --from=builder --chown=app:app /app/server .

USER app

EXPOSE 8080

CMD ["./server"]
```

### docker-compose.yml (Local Dev)

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./src:/app/src:ro  # Hot reload in dev

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### .dockerignore

```
# Git
.git
.gitignore

# Dependencies (rebuilt in container)
node_modules
.venv
__pycache__

# Build artifacts
dist
build
*.egg-info

# IDE
.vscode
.idea

# Environment (secrets)
.env
.env.local
.env.*.local

# Testing
coverage
.pytest_cache
.nyc_output

# Agent artifacts
.agents

# OS
.DS_Store
Thumbs.db
```

---

## Infrastructure as Code

### Pulumi over Terraform

| Feature | Pulumi | Terraform |
|---------|--------|-----------|
| Language | TypeScript, Python, Go | HCL (proprietary) |
| IDE Support | Full (types, autocomplete) | Limited |
| Testing | Standard unit tests | Separate tooling |
| Logic | Real conditionals, loops | Limited HCL constructs |
| State | Pulumi Cloud or self-hosted | Terraform Cloud or self-hosted |

### Pulumi Setup (TypeScript)

```bash
# Install Pulumi
brew install pulumi

# Create new project
mkdir infra && cd infra
pulumi new typescript

# Install AWS provider (or gcp, azure, etc.)
bun add @pulumi/aws
```

### Example: AWS ECS + RDS

```typescript
// infra/index.ts
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const config = new pulumi.Config();
const environment = pulumi.getStack(); // dev, staging, prod

// VPC
const vpc = new aws.ec2.Vpc("vpc", {
  cidrBlock: "10.0.0.0/16",
  enableDnsHostnames: true,
  tags: { Name: `${environment}-vpc` },
});

// RDS PostgreSQL
const db = new aws.rds.Instance("db", {
  engine: "postgres",
  engineVersion: "16",
  instanceClass: "db.t3.micro",
  allocatedStorage: 20,
  dbName: "app",
  username: "postgres",
  password: config.requireSecret("dbPassword"),
  skipFinalSnapshot: true,
  vpcSecurityGroupIds: [dbSecurityGroup.id],
  dbSubnetGroupName: dbSubnetGroup.name,
});

// ECS Cluster
const cluster = new aws.ecs.Cluster("cluster", {
  name: `${environment}-cluster`,
});

// Export outputs
export const dbEndpoint = db.endpoint;
export const clusterArn = cluster.arn;
```

### Pulumi Setup (Python)

```bash
pulumi new python

# Install providers
uv add pulumi-aws
```

```python
# infra/__main__.py
import pulumi
import pulumi_aws as aws

config = pulumi.Config()
environment = pulumi.get_stack()

# VPC
vpc = aws.ec2.Vpc(
    "vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    tags={"Name": f"{environment}-vpc"},
)

# Export
pulumi.export("vpc_id", vpc.id)
```

---

## Database Migrations

### Atlas (for Python/SQLAlchemy)

```bash
# Install Atlas
brew install ariga/tap/atlas

# Generate migration from schema diff
atlas migrate diff migration_name \
  --to "file://schema.sql" \
  --dev-url "postgres://localhost:5432/dev?sslmode=disable"

# Apply migrations
atlas migrate apply \
  --url "postgres://localhost:5432/app?sslmode=disable"
```

### Drizzle Kit (for TypeScript)

```bash
# Generate migration
bun run db:generate

# Apply migration
bun run db:migrate

# Open studio
bun run db:studio
```

### golang-migrate (for Go)

```bash
# Install
brew install golang-migrate

# Create migration
migrate create -ext sql -dir migrations -seq create_users_table

# Apply
migrate -path migrations -database "$DATABASE_URL" up

# Rollback
migrate -path migrations -database "$DATABASE_URL" down 1
```

---

## CI/CD Patterns

### GitHub Actions (General)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Language-specific setup
      # ...

      - name: Lint
        run: just lint

      - name: Test
        run: just test

      - name: Build
        run: just build
```

### Deploy Pattern

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: railwayapp/railway-cli@v1
        with:
          service: my-service
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## When to Add What

| Need | Tool | Notes |
|------|------|-------|
| Task runner | Just | Simple, cross-platform. Alternative: Task (taskfile.dev) for YAML fans. |
| Local dev with dependencies | docker-compose | Postgres, Redis, etc. |
| Deploy to cloud | Dockerfile | Production container |
| Multi-environment infra | Pulumi | Dev, staging, prod |
| Database schema management | Atlas / Drizzle Kit | Depends on language |
| CI/CD | GitHub Actions | Or Railway/Vercel auto-deploy |

### Task Runners: Just vs Task

We use **Just** (justfile) because it's simpler and feels like a modern Makefile. **Task** (taskfile.dev) is a valid alternative if you prefer YAML syntax.

| Feature | Just | Task |
|---------|------|------|
| Syntax | Makefile-like | YAML |
| Dependencies | Implicit | Explicit `deps:` field |
| Variables | Shell-style | Go templates |
| Learning curve | Lower | Slightly higher |

Both work well. Pick one and stick with it.

**Start simple**: Most projects can deploy directly to Railway/Vercel without any Docker or Pulumi. Add infrastructure tooling when you actually need it.

---

## Cloud Vendor Recommendations

> See `shared/SERVICES.md` for detailed service comparisons.

### Quick Picks

| Category | Primary | Alternative |
|----------|---------|-------------|
| **Hosting** | Railway | Cloudflare (edge), Fly.io (VMs) |
| **Database** | Supabase | Neon, Turso (edge) |
| **Cache** | Valkey (self-hosted) | Upstash (serverless) |
| **Search** | Meilisearch (self-hosted) | Orama (browser) |
| **Auth** | Better Auth (self-hosted) | Clerk (managed) |
| **Email** | Resend | Postmark |
| **Analytics** | Umami (self-hosted) | Plausible |
| **Payments** | Stripe | LemonSqueezy (MoR) |

### Avoid

- **Firebase**: Vendor lock-in, proprietary queries
- **Heroku**: Expensive, stagnant
- **AWS/GCP/Azure directly**: Complexity overhead (use Railway/Fly.io instead)

---

## Observability

### Tiers

```
Tier 1 - Essential (All Projects)
├── structlog / pino (structured logging)
└── Sentry (error tracking, alerts)

Tier 2 - Multi-Service (2+ services calling each other)
├── OpenTelemetry instrumentation
├── Trace IDs in logs
└── Basic metrics (Prometheus if K8s)

Tier 3 - At Scale (production systems with SLOs)
├── Jaeger or Grafana Tempo (distributed tracing)
├── Grafana dashboards
├── Prometheus + Alertmanager
└── Full OTel correlation
```

### OpenTelemetry Setup (Python)

```python
# Add when you have 2+ services that call each other
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_telemetry(app):
    """Initialize OpenTelemetry tracing."""
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_fastapi_app(app)
    # Auto-instrument outgoing HTTP calls
    HTTPXClientInstrumentor().instrument()
```

### OpenTelemetry Setup (TypeScript)

```typescript
// Add when you have 2+ services that call each other
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://jaeger:4317' }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

### Sentry Setup

```bash
# Python
uv add sentry-sdk

# TypeScript
bun add @sentry/node
```

```python
# Python - add to app startup
import sentry_sdk

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=0.1,  # 10% of transactions
    environment=settings.environment,
)
```

```typescript
// TypeScript - add to app startup
import * as Sentry from '@sentry/node';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
});
```

### docker-compose with Observability Stack

```yaml
# Add to docker-compose.yml for local development
services:
  jaeger:
    image: jaegertracing/all-in-one:1.53
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
    environment:
      COLLECTOR_OTLP_ENABLED: true

  prometheus:
    image: prom/prometheus:v2.48.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
```
