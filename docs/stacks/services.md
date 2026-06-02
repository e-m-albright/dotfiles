# Cloud Services Reference

**Philosophy**: Self-hosted first when practical. Managed services when self-hosting becomes a burden.

> **Note**: This is a menu, not a mandate. Most projects need only 2-3 services.
> A simple app needs hosting + database. Add services as requirements emerge.

---

## Decision Framework

```
                    ┌─────────────────┐
                    │ Do you need it? │
                    └────────┬────────┘
                             │ yes
                    ┌────────▼────────┐
                    │ Can you         │
                    │ self-host it?   │
                    └────────┬────────┘
                      yes    │    no
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌───────────┐    ┌───────────────┐
            │ Self-host │    │ Use managed   │
            │ (Railway, │    │ service       │
            │  Docker)  │    │               │
            └───────────┘    └───────────────┘
```

---

## Hosting

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **General** | Railway | Render | Railway: better DX, nixpacks. Render: cheaper for static. |
| **Edge/Static** | Cloudflare Pages | Vercel | Cloudflare: free tier, Workers. Vercel: Next.js native. |
| **Containers** | Fly.io | Railway | Fly.io: global edge, VMs. Railway: simpler PaaS. |

### When to Use What

- **Railway**: Default for most backend services. Great DX, easy scaling.
- **Cloudflare**: Static sites, edge functions, anything latency-sensitive.
- **Fly.io**: When you need VMs, global distribution, or SQLite (LiteFS).
- **Render**: Budget option, good for simple services.

---

## Infrastructure as Code

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **AWS + TypeScript** | SST | AWS CDK | SST: full-stack IaC in one `sst.config.ts`, Pulumi under the hood, fast local dev. CDK: lower level, use only for resources SST doesn't expose. |
| **Multi-Cloud** | Pulumi | Terraform / OpenTofu | Pulumi: real languages (TS/Python/Go). Terraform: industry standard (HCL), huge ecosystem. OpenTofu: OSS fork after HashiCorp license change. |

### When to Use What

- **SST**: Default for AWS + TypeScript. Defines Lambda, RDS, S3, queues, frontends in one config. Skip if you need multi-cloud.
- **Pulumi**: Multi-cloud or when SST doesn't cover your resource. More verbose but more flexible.
- **Terraform/OpenTofu**: Large infra teams, multi-cloud at scale. Overkill for solo devs on AWS.
- **AWS CDK**: SST is strictly better DX. Only use raw CDK for L3 constructs SST doesn't expose.

---

## Database

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Managed Postgres** | Supabase | Neon | Supabase: Postgres + auth + storage. Neon: pure Postgres, branching, scale-to-zero. |
| **Managed MySQL** | PlanetScale | — | Serverless MySQL on Vitess (YouTube's scaler). DB branching, non-blocking migrations. Killed free tier in 2024 ($39/mo min). |
| **Edge SQLite** | Turso | Cloudflare D1 | Turso: libSQL, replicas, cheap per-tenant isolation. D1: Cloudflare-native. |
| **Self-Hosted** | PostgreSQL on Railway | — | Just deploy a Postgres container. |

### When to Use What

- **Supabase**: Need Postgres + extras (auth, storage, realtime). Good free tier.
- **Neon**: Pure Postgres, need database branching for previews. Default "Postgres with nice devex."
- **PlanetScale**: Strong if you need MySQL or massive horizontal scale. Fewer ecosystem tools than Postgres.
- **Turso**: Edge-first, SQLite-compatible, global reads. Per-tenant DB isolation is cheap — good for multi-tenant SaaS with audit boundaries.

### Supabase Accelerators

| Tool | Purpose | Notes |
|------|---------|-------|
| **Basejump** | Multi-tenant SaaS | Pre-built RLS policies, team/org management, billing integration. Huge time saver. |

---

## NoSQL / Key-Value / Document

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **AWS Native KV** | DynamoDB | — | Single-digit ms at any scale. Pairs with Lambda/SST. Demands access-pattern-first design. |
| **Document DB** | MongoDB Atlas | — | Flexible JSON docs, aggregation pipeline, built-in full-text search. Less relevant if already using Postgres with JSONB. |
| **Cache + Queues** | Valkey / Upstash | Dragonfly | Valkey: Redis fork (self-hosted). Upstash: serverless Redis, per-request billing. Dragonfly: extreme perf. |

### When to Use What

- **DynamoDB**: Known, high-throughput access patterns (sessions, event logs, webhook state). Painful for flexible queries. Most solo devs should start with Postgres and migrate if they hit the wall.
- **MongoDB Atlas**: Variable-schema data, need full-text search without a separate service. Atlas Search is genuinely useful.
- **Valkey/Upstash**: Almost always needed alongside a primary DB for caching, rate limiting, pub/sub, sessions. Upstash pairs well with serverless (Railway/Vercel) — no persistent server to manage.

---

## Analytics (OLAP)

> **For heavy analytical queries.** Most apps don't need this—Postgres is fine for dashboards.

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **In-Process** | DuckDB | — | Query Postgres/Parquet with SQL. No server needed. Embeds in Python/Node/Rust. |
| **Managed** | Tinybird | ClickHouse Cloud | Tinybird: API-first, real-time. ClickHouse: raw power, millions of rows/sec ingest. |
| **Self-Hosted** | ClickHouse | — | Only for serious OLAP workloads at scale. |
| **Data Warehouse** | Snowflake | BigQuery | Snowflake: multi-cloud, excellent data sharing across orgs. BigQuery: GCP-native, pay-per-query, petabyte-scale. Both integrate with dbt. |

### When to Use What

- **DuckDB**: Default for analytics. Query your existing data without infrastructure.
- **Tinybird**: Real-time analytics APIs, user-facing dashboards, event streaming.
- **ClickHouse**: When DuckDB isn't fast enough (rare). Petabyte-scale analytics.

> **Note**: Most SaaS apps should start with Postgres + DuckDB. Add ClickHouse/Tinybird when you have millions of events and need sub-second queries. Snowflake/BigQuery are for enterprise data integrations — large pharma almost certainly has Snowflake.

---

## Search

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Full-Text** | Meilisearch | Typesense | Meilisearch: easier setup. Typesense: more features. |
| **In-Browser** | Orama | Pagefind | Orama: full-featured. Pagefind: static site search. |

### Self-Hosting Meilisearch

```yaml
# docker-compose.yml
services:
  meilisearch:
    image: getmeili/meilisearch:v1.35
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
    volumes:
      - meilisearch_data:/meili_data
    ports:
      - "7700:7700"
```

> **Managed Option**: Meilisearch Cloud when self-hosting becomes a burden.

---

## Email

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Transactional** | Resend | Postmark | Resend: modern DX, React Email. Postmark: deliverability focus. |
| **Marketing** | — | — | Skip until you need it. Use Resend for basic emails. |

### Resend Example

```typescript
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

await resend.emails.send({
  from: 'noreply@yourdomain.com',
  to: user.email,
  subject: 'Welcome!',
  react: <WelcomeEmail name={user.name} />,
});
```

---

## Authentication

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Self-Hosted** | Better Auth | — | Full-featured, TypeScript-first, active development. |
| **Managed** | Clerk | Auth0 | Clerk: modern DX. Auth0: enterprise features. |

### When to Use What

- **Better Auth**: Default. Self-hosted, full control, TypeScript-first, excellent SvelteKit integration.
- **Clerk**: When you don't want to manage auth infrastructure.

### Better Auth Setup

```typescript
// auth.ts
import { betterAuth } from 'better-auth';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: 'pg' }),
  emailAndPassword: { enabled: true },
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    },
  },
});
```

---

## Analytics

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Privacy-First** | Umami | Plausible | Both self-hostable. Umami: free. Plausible: polished. |
| **Product Analytics** | PostHog | — | When you need funnels, feature flags, session replay. |

### Self-Hosting Umami

```yaml
# docker-compose.yml
services:
  umami:
    image: ghcr.io/umami-software/umami:postgresql-latest
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/umami
      DATABASE_TYPE: postgresql
    ports:
      - "3000:3000"
```

---

## Caching

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Self-Hosted** | Valkey | Dragonfly | Valkey: Redis fork (post-license change). Dragonfly: faster. |
| **Managed** | Upstash | — | Serverless Redis. Pay per request. |

### When to Use What

- **Valkey**: Default for self-hosted. Drop-in Redis replacement.
- **Upstash**: Serverless, don't want to manage infrastructure.
- **Dragonfly**: Need extreme performance, drop-in Redis replacement.

---

## Queues / Event Streaming

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **AWS Native** | SQS / SNS | — | SQS: managed queue (pull). SNS: pub/sub (push). Both integrate with Lambda/SST natively. No ops. |
| **High-Throughput** | Kafka / Redpanda | — | Log-based streaming. Replay, fan-out, history retention. Redpanda: Kafka-compatible, faster, simpler ops. |
| **Serverless** | Upstash Kafka / QStash | — | Serverless Kafka + HTTP job queues. QStash: great for delayed jobs from serverless functions. |

### When to Use What

- **SQS/SNS**: Default if you're on AWS. SST wires them to Lambda trivially.
- **Kafka/Redpanda**: Real-time data feeds, event sourcing, audit logs at scale. Overkill for most early-stage apps.
- **QStash**: Underrated for webhook delivery and scheduled jobs from serverless (Railway/Vercel). No persistent server needed.

---

## Durable Execution / Workflows

> **For multi-step workflows that must survive a crash and resume from the last completed step** — strictly stronger than a queue (which only retries the whole job). The 2026 split is *library-on-Postgres* vs *server-you-operate*; for a Postgres-centric solo/small stack the former wins.

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Lightweight (library)** | DBOS | — | Postgres-only, runs *inside* your app process (Python/TS/Go). The "lightweight Temporal" — durability with zero new infra. Best default. |
| **Go background jobs** | River | asynq | Postgres-backed, transactional enqueue. A queue, not full durable execution. |
| **TS event-driven** | Inngest | Trigger.dev | Inngest: light self-host (single binary). Trigger.dev: more of a platform (registry + object storage). |
| **Heavy-duty** | Temporal | Restate (watch) | Cross-language, mission-critical scale. The cluster (Cassandra/ES) is real ops burden — reach for it only when correctness-at-scale demands it. |

### When to Use What

- **DBOS**: Default. A library, not a server — `pip install`/`npm i`, point at existing Postgres, decorate workflow/step functions. Matches the "Postgres as the only dependency" ethos. Free OSS core; only the ops console is paid.
- **Temporal**: When you genuinely need multi-DC, millions of concurrent workflows, or cross-service orchestration. Self-hosting the cluster is exactly the ops burden most projects should avoid; even Temporal concedes Cloud beats self-host economically below tens of millions of actions/month.
- **Plain Postgres + cron / Arq / River / QStash**: When the real need is "run on a schedule" or "a few retryable jobs." Durable execution only pays off once you have genuinely multi-step workflows with side effects you must not re-run.

---

## Realtime / Local-First Sync

> **For offline-first or live-multiplayer UIs.** A "solution looking for a problem" trap — don't adopt speculatively. Add only when there's a concrete offline/realtime requirement.

| Need | Pick | Notes |
|------|------|-------|
| Read-sync on your own Postgres | **ElectricSQL** | Postgres → client SQLite via declarative "shapes"; OSS, self-hostable. Best fit for a Postgres-centric SvelteKit shop. |
| Mobile/offline, production-tested | PowerSync | You own writes/conflict resolution via your API. |
| Collaborative text/rich-doc editing | Yjs | CRDT library — the right tool for collaborative editing, not structured-data sync. |
| General-purpose sync (watch) | Rocicorp Zero | Ambitious; still alpha — watch, don't build on yet. |

Convex / Liveblocks / PartyKit trade self-host-first for hosted DX — fine for speed, but a platform dependency.

---

## Payments

| Category | Primary Pick | Notes |
|----------|-------------|-------|
| **Payments** | Stripe | Industry standard. No real alternative at this level. |
| **Alternative** | LemonSqueezy | Merchant of record. Handles taxes for you. |

> **Note**: Use Stripe unless you specifically need merchant-of-record (LemonSqueezy handles sales tax/VAT).

---

## Observability

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Error Tracking** | Sentry | — | Industry standard. Excellent SDKs. |
| **Logs** | Grafana Cloud | Axiom | Grafana: full stack. Axiom: simpler, generous free tier. |
| **Tracing** | Jaeger | Grafana Tempo | Self-host Jaeger. Or use Grafana Tempo in Grafana Cloud. |

### Observability Tiers

```
Tier 1 (All Projects):
├── structlog / pino (logging)
└── Sentry (error tracking)

Tier 2 (2+ Services):
├── OpenTelemetry instrumentation
└── Basic metrics

Tier 3 (At Scale):
├── Jaeger / Grafana Tempo (tracing)
├── Grafana dashboards
└── Prometheus (metrics)
```

---

## Quick Reference: What to Use When

| Project Type | Services |
|-------------|----------|
| Simple API | Railway + Supabase + Sentry |
| + Auth | add Better Auth |
| + Email | add Resend |
| + Search | add Meilisearch (self-hosted) |
| + Caching/Queues | add Upstash (Redis + QStash) |
| SaaS Product | above + Stripe + Umami + PostHog |
| + AI Features | add Modal or pgvector |
| + IaC | SST (AWS) or Pulumi (multi-cloud) |
| At Scale | add Grafana Cloud + OpenTelemetry |
| + Analytics | add ClickHouse or Snowflake |
| + Event Streaming | add SQS/SNS (AWS) or Redpanda |
| Enterprise Data Integration | Snowflake or BigQuery + dbt |

---

## AI Infrastructure

> **For running ML models and AI workloads**, not for coding assistance.

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Serverless GPU** | Modal | Replicate | Modal: full control, Python-native. Replicate: pre-built models, API-first. |
| **Model Hosting** | Replicate | Baseten | Replicate: easy API. Baseten: more customization, self-hosted option. |

### When to Use What

- **Modal**: Default for custom AI workloads. Python-native, excellent DX, auto-scaling GPUs.
- **Replicate**: Running pre-trained models via API. Quick integration, no infra management.
- **Baseten**: Enterprise needs, self-hosted requirements.

### Modal Example

```python
import modal

app = modal.App("my-ai-service")

@app.function(gpu="A10G")
def run_inference(prompt: str) -> str:
    # Your model code here
    return result
```

> **Note**: For simple embeddings or completions, just use OpenAI/Anthropic APIs directly. Modal/Replicate are for custom models or heavy inference workloads.

---

## Vector Databases

> **For semantic search and RAG applications.** Most projects should start with pgvector.

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Postgres Extension** | pgvector | — | Add to existing Postgres. Good enough for most use cases. |
| **Managed Vector DB** | Pinecone | Weaviate Cloud | Pinecone: simple, fast. Weaviate: more features. |
| **Self-Hosted** | Qdrant | Milvus, Weaviate | Qdrant: best DX. Milvus: highest scale. |
| **Embedded** | LanceDB | Chroma | LanceDB: serverless, multimodal. Chroma: simpler. |
| **Library** | FAISS | — | Meta's similarity search. Embed in apps, not a full DB. |

### Decision Tree

```
How much vector data?
├── < 1M vectors → pgvector (in your existing Postgres)
├── 1M-100M vectors → Qdrant or Pinecone
└── > 100M vectors → Milvus or dedicated solution
```

### pgvector Setup (Supabase)

```sql
-- Enable the extension
create extension vector;

-- Add vector column
alter table documents add column embedding vector(1536);

-- Create index for fast similarity search
create index on documents using ivfflat (embedding vector_cosine_ops);
```

> **Recommendation**: Start with pgvector. Only move to dedicated vector DBs when you hit scale limits or need advanced features (hybrid search, filtering, etc.).

---

## Anti-Recommendations

| Service | Why to Avoid |
|---------|-------------|
| Firebase | Vendor lock-in, proprietary query language. |
| Heroku | Pricing, removed free tier, stagnant. |
| Auth0 | Complex, expensive, enterprise-focused. |
| Datadog/New Relic | Overkill for small teams, expensive. |
| AWS/GCP/Azure directly | Complexity overhead. Use Railway/Fly.io instead. |
| Vercel | Pricing traps, vendor lock-in, Next.js-centric. Use Railway or Cloudflare instead. |
| Next.js | Vercel-coupled, complexity creep. Use SvelteKit or Astro instead. |
