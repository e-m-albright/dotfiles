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
FROM python:3.14-slim as builder

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.14-slim

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
FROM golang:1.25-alpine as builder

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

> **When to use IaC**: Most projects can deploy directly to Railway, Vercel, or Fly.io without any IaC.
> Add Pulumi when you need multi-environment infrastructure (dev/staging/prod) or complex AWS/GCP setups.

### CLI Tools (Install When Needed)

These are **not installed globally** — add them per-project or enable in `brew.sh` when needed:

| Tool | Purpose | Install |
|------|---------|---------|
| **awscli** | AWS CLI | `brew install awscli` |
| **leapp** | Cloud credentials manager | `brew install --cask leapp` |
| **geodesic** | Cloud automation shell | `brew install cloudposse/tap/geodesic` |
| **atmos** | Terraform orchestration | `brew install cloudposse/tap/atmos` |
| **opentofu** | Open-source Terraform fork | `brew install opentofu` |
| **doppler** | Secrets management | `brew install dopplerhq/cli/doppler` |

> **Note**: Prefer OpenTofu over Terraform (open-source, compatible). Use Doppler for secrets management across environments.

### Pulumi (Consider for Later)

Pulumi lets you define infrastructure in TypeScript/Python/Go instead of HCL. Benefits over Terraform:

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
| Pin per-project tool versions | **mise** | Polyglot version manager (Go/Node/Rust/terraform/etc.) + env + tasks. Sits *under* uv/Bun (which own their language); earns its place once a repo spans 2+ languages or needs a non-Python/JS tool pinned. Subsumes asdf/nvm/pyenv/direnv. |
| Local dev with dependencies | docker-compose | Postgres, Redis, etc. |
| Reverse proxy + auto-HTTPS | **Caddy** | 3-line config, automatic Let's Encrypt, auto-renew. Over Traefik (needs dynamic container discovery) / nginx (needs fine tuning) for a solo dev. |
| Expose local dev | **cloudflared** | Tunnel onto your own domain (dev→prod parity, free WAF). ngrok for throwaway/webhook-debugging; Tailscale Funnel if already meshed. |
| API client (collections-as-code) | **Bruno** | Git-native `.bru` files in-repo, offline, no SaaS lock-in. Postman/Insomnia replacement. |
| API smoke tests in CI | **Hurl** | Plain-text `.hurl` files, single binary, JUnit output. Black-box endpoint assertions, not business-logic coverage. |
| Changelog / releases | **git-cliff** | Conventional-commits → changelog, single binary, language-agnostic. changesets only for a multi-package TS monorepo. |
| Diagrams in docs | **Mermaid** | Renders natively in GitHub/PRs, no build step; agents write it fluently. D2 only for big architecture diagrams where you'll own a render step. |
| Deploy to cloud | Dockerfile | Production container |
| Multi-environment infra | Pulumi | Dev, staging, prod — but see the CLI-scripted counterpoint below |
| Database schema management | Atlas / Drizzle Kit | Depends on language |
| CI/CD | GitHub Actions | Or Railway/Vercel auto-deploy. **CI should call task-runner recipes, not hold logic** — see [knowledge/engineering-gates.md](../knowledge/engineering-gates.md) |

### When CLI-scripted provisioning beats full IaC

Pulumi/SST/Terraform earn their keep with multi-environment fleets and large resource graphs. But for a **single operator with a handful of long-lived cloud resources**, a full IaC tool can be more ceremony than payoff. A legitimate alternative: an **idempotent Bash `setup.sh` orchestrating the vendor CLIs** (your host's CLI, your DB provider's CLI, your secrets CLI), where every "create" is guarded to skip existing resources and any values it provisions are written back into the secrets manager. Pair it with **change-detection deploys** (skip a service whose source paths didn't change since its deployed revision) and **health-gated ordering** (deploy a dependency, wait for healthy, then its clients). The vendor CLIs *are* the real API; for small polyglot apps this can be simpler and more debuggable than a state-file abstraction over them.

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

### Production topology: OTEL Collector → backend

Once you have 2+ services, don't export from each app SDK straight to a vendor. Run **one OpenTelemetry Collector** (its own small service) that every app sends OTLP to; it batches, filters, transforms, and fans out to the backend (**Axiom** for logs/traces with a generous free tier, or Grafana Cloud). Rust (`tracing` → OTLP/gRPC), Python (`structlog` → OTLP/gRPC), and the web tier (`@opentelemetry` browser + node → OTLP/HTTP) all point at the internal collector. Default `OTEL_ENABLED=false` locally.

Why the collector and not direct export:

- **Disk-backed queue** (`file_storage` extension on a volume) buffers spans during a deploy and replays them once the new instance is healthy — no telemetry gap across rollouts.
- **Per-signal datasets** — keep metrics in a separate dataset from traces/logs so metric cardinality can't blow up the operational-events store.
- **Attribute-cardinality packing** — columnar backends (Axiom et al.) flatten every unique attribute key into a column and cap at ~256 fields/dataset. A `transform` processor that packs non-semconv custom attributes into a single nested `map` column (keeping only `gen_ai.*`/`http.*`/`db.*`/`exception.*` flat) keeps you under the cap.

### Observability footguns (each fails silently in the layer it lives in)

- **Telemetry export must be async/fail-fast on hot paths.** A blocking exporter (e.g. one holding Python's GIL) on an async service starves the event loop → liveness probe fails → the platform proxy returns 503 to *all* callers, killing unrelated work. A blocking exporter whose endpoint is unreachable can burn most of a request's latency budget on retries. If a tracing SDK can't be made non-blocking on the hot path, keep it off in prod.
- **Exclude health/liveness endpoints from spans.** Probe traffic otherwise becomes your dominant telemetry volume and amplifies any exporter problem. Filter by *multiple* attributes (span name, `http.target`, `http.url`) — instrumentation populates them inconsistently, so matching only one misses.
- **OTLP gRPC metadata keys must be lowercase.** An uppercase `Authorization` header is silently rejected — observability goes dark with no error anywhere.

### Fly.io operational notes

If you deploy to Fly (the services.md "containers / global edge" pick):

- **Safe always-on combo is `auto_stop_machines = "off"` + `auto_start_machines = true`.** The forbidden pairing is `auto_stop="off"` + `auto_start=false` — it leaves stopped machines stuck stopped. With autostart on, the first health-check after a rolling deploy wakes the swapped machine (green deploy, not a 503).
- **A persistent volume forces `strategy = "rolling"`, not `bluegreen`** — a Fly volume attaches to one machine at a time, so a green machine fails with `volume already claimed`. Move state to object storage to regain blue-green.
- **Use `[[vm]]` (double bracket).** Singular `[vm]` is silently ignored — verify VM sizing post-deploy rather than trusting the toml.
- **Internal-only services still need `auto_start`/`min_machines_running`** — internal callers traverse the same proxy as public traffic.

### Build discipline

- **Rust images: cargo-chef + mold.** `cargo-chef` caches the dependency-compile layer; `mold` is a fast linker. Together they cut Rust image rebuilds dramatically. Build with `SQLX_OFFLINE=true` against committed `.sqlx/` metadata so the image build never needs a live DB; regenerate `.sqlx/` when SQL changes, and treat applied migrations as immutable (never edit them — checksum mismatch).
- **Python images: `uv sync --frozen --no-dev`**, uv binary copied from its official image.
- **SvelteKit: build with Bun, run on Node** — `oven/bun:1` for `bun install --frozen-lockfile` + `bun run build`, then `node:22-slim` running `node build/index.js`.
- **Pin toolchains exactly** (`rust-toolchain.toml`, `mise` versions) so CI and local agree on lint behavior; bump deliberately via PR.
