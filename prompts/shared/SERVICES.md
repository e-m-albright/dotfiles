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

## Database

| Category | Primary Pick | Alternative | Notes |
|----------|-------------|-------------|-------|
| **Managed Postgres** | Supabase | Neon | Supabase: Postgres + auth + storage. Neon: pure Postgres, branching. |
| **Edge SQLite** | Turso | Cloudflare D1 | Turso: libSQL, replicas. D1: Cloudflare-native. |
| **Self-Hosted** | PostgreSQL on Railway | — | Just deploy a Postgres container. |

### When to Use What

- **Supabase**: Need Postgres + extras (auth, storage, realtime). Good free tier.
- **Neon**: Pure Postgres, need database branching for previews.
- **Turso**: Edge-first, SQLite-compatible, global reads.

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
    image: getmeili/meilisearch:v1.6
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
| **Self-Hosted** | Better Auth | Lucia | Better Auth: full-featured. Lucia: lightweight, DIY. |
| **Managed** | Clerk | Auth0 | Clerk: modern DX. Auth0: enterprise features. |

### When to Use What

- **Better Auth**: Default. Self-hosted, full control, TypeScript-first.
- **Lucia**: Lightweight auth primitives. When you want to build your own.
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
| SaaS Product | above + Stripe + Umami + PostHog |
| + AI Features | add Modal or pgvector |
| At Scale | add Grafana Cloud + OpenTelemetry |

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
