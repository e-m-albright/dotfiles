# TypeScript Stack

**Philosophy**: Modern, type-safe, full-stack web development with maximum DX.

> **Note**: This is a menu, not a mandate. A simple landing page doesn't need DuckDB.
> Start with the core (Bun, SvelteKit, Tailwind) and add tools as requirements emerge.

---

## Installation Phases

Tools are grouped by when to add them. Start with Phase 1, add others as needed.

```
Phase 1 - ALWAYS (every project)     Phase 2 - WHEN NEEDED (specific features)
├── Bun (runtime + package manager)  ├── Drizzle + Better Auth (user data)
├── SvelteKit 2 + Svelte 5           ├── TanStack Query (complex data fetching)
├── Tailwind CSS v4                  ├── Resend (email)
├── Biome (lint + format)            ├── Meilisearch (search)
├── Just (task runner)               ├── Stripe (payments)
└── Lefthook (git hooks)             └── LayerChart (data viz)

Phase 3 - SCALE / SPECIAL
├── Tauri (desktop app)
├── DuckDB-WASM (client analytics)
└── OpenTelemetry (2+ services)
```

---

## Runtime & Tooling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Runtime** | Bun | Node.js is slower; Deno has ecosystem gaps. Bun is 3-4x faster, native TypeScript, built-in test runner. |
| **Package Manager** | Bun | pnpm is good but Bun is faster and eliminates tool sprawl. |
| **Linter/Formatter** | Biome | ESLint + Prettier is slow and requires config hell. Biome is 35x faster, single tool, Rust-based. |
| **Git Hooks** | Lefthook | Husky is slower, JS-based. Lefthook is Go-based, parallel execution, YAML config. |
| **Task Runner** | Just | npm scripts are limited; Make syntax is archaic. Just is readable, cross-platform, modern. |

---

## Framework & Build

**Pick based on use case:**

| Use Case | Framework | Notes |
|----------|-----------|-------|
| Full-stack web app | SvelteKit 2 | SSR, API routes, forms, auth |
| Content site / blog | Astro | Content collections, islands, MDX, static-first |
| Marketing / landing | Astro | Or SvelteKit with static adapter |
| Dashboard / SaaS | SvelteKit 2 | Better for highly interactive UIs |

### SvelteKit (Full-Stack Apps)

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | SvelteKit 2 | Next.js is React (more boilerplate); Nuxt is Vue (less type-safe). SvelteKit is simpler, faster, better DX. |
| **UI Framework** | Svelte 5 | React has hooks complexity; Vue has Options/Composition duality. Svelte 5 runes are intuitive and performant. |
| **Build** | Vite | Built into SvelteKit. Webpack is slow; Turbopack is React-only. |
| **Adapter** | svelte-adapter-bun | Native Bun integration for production. |

### Astro (Content Sites)

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | Astro 4/5 | Zero JS by default, content collections, islands architecture. Perfect for blogs, docs, marketing. |
| **UI Components** | Svelte (via @astrojs/svelte) | Use Svelte for interactive islands. React/Vue also supported but Svelte is lighter. |
| **Content** | MDX (@astrojs/mdx) | Components in Markdown. Or plain Markdown for simple content. |
| **Build** | Vite | Built into Astro. |
| **Adapter** | @astrojs/cloudflare | Or @astrojs/node, @astrojs/vercel based on deployment target. |

> **When to use Astro over SvelteKit**: Content-heavy sites (blogs, docs, portfolios) where most pages are static. Astro's content collections and zero-JS default are ideal. Add Svelte components for interactive islands.

---

## State & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Server State** | TanStack Query (Svelte) | SWR is React-only. TanStack has better devtools, mutations, infinite queries. |
| **Client State** | Svelte 5 Runes | Built-in. Zustand/Jotai are React-centric; Svelte's reactivity is superior. |
| **Forms** | Superforms + Zod | Formik is React-only; react-hook-form is complex. Superforms is SvelteKit-native with progressive enhancement. |
| **Validation** | Zod | Yup has worse TypeScript inference. Zod is TS-first with excellent DX. |

---

## UI & Styling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Styling** | Tailwind CSS v4 | CSS-in-JS has runtime cost; Sass is verbose. Tailwind v4 is CSS-first, faster, smaller. |
| **Components** | shadcn-svelte + Bits UI | Chakra/MUI are heavy, React-only. shadcn is copy-paste, customizable, accessible via Bits UI. |
| **Charts** | LayerChart | Recharts is React-only; Chart.js lacks customization. LayerChart is Svelte-native, D3-powered. |
| **Animations** | Svelte transitions | Framer Motion is React-only. Svelte has excellent built-in transitions. |

---

## Database & Backend

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **ORM** | Drizzle | Prisma has Bun compatibility issues, slower cold starts. Drizzle is type-safe SQL, faster, lighter. |
| **Database** | PostgreSQL | SQLite lacks concurrent writes for production. Postgres is the industry standard. |
| **Migrations** | drizzle-kit | Prisma Migrate is slower. drizzle-kit generates clean SQL migrations. |
| **Schema Sync** | drizzle-zod | Generates Zod schemas from Drizzle tables. Single source of truth. |

---

## Auth

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Auth** | Better Auth | Full-featured, TypeScript-first, self-hosted. Has OAuth, magic links, 2FA out of the box. |
| **Alternative** | Lucia | Lightweight auth primitives. Use when you want to build your own auth flow. |
| **Managed** | Clerk | When you don't want to self-host auth. Modern DX but external dependency. |

> **Note**: Better Auth over Lucia for most projects. Lucia is for when you want more control.

---

## Analytics & Data (add when needed)

> **Only add these when your project actually needs analytics.** Most apps don't need DuckDB.

| Category | Choice | When to Use |
|----------|--------|-------------|
| **In-Browser Analytics** | DuckDB-WASM | Heavy client-side data processing. Query Parquet files in browser. |
| **DataFrames** | Polars.js | If you need Polars-style operations in JS. Consider doing analytics server-side in Python instead. |
| **Server Analytics** | DuckDB | Server-side analytics on Postgres or Parquet data. |

> **Recommendation**: For serious analytics, consider a Python service with Polars/DuckDB rather than doing it in TypeScript.

---

## Testing

**Match testing to complexity.** Not every project needs the same testing infrastructure.

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Unit** | Vitest | Jest is slower, needs more config. Vitest is Vite-native, faster, better DX. |
| **Component** | @testing-library/svelte | Enzyme is dead. Testing Library focuses on user behavior, not implementation. |
| **E2E** | Playwright | Cypress is slower, limited cross-browser. Playwright is faster, better debugging. |
| **Mocking** | MSW | Nock is Node-only. MSW works in browser and Node, intercepts at network level. |

### When to Use What

| Project Type | Testing Strategy |
|--------------|------------------|
| **Static site / blog (Astro)** | `astro check` + Biome. If it builds, it works. Unit test utilities if complex. |
| **Content site with islands** | Above + Vitest for interactive components. |
| **SvelteKit app (no auth)** | Vitest for logic + components. |
| **SvelteKit app (auth/forms)** | Full stack: Vitest + Playwright for critical flows. |
| **SaaS / Dashboard** | Full stack + MSW for API mocking. |

> **Astro sites**: E2E testing is usually overkill. Astro validates content collections at build time, and static content either renders or fails the build. Save Playwright for apps with auth, forms, and complex user interactions.

---

## Code Quality

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Linting** | Biome | ESLint + plugins is slow. Biome is all-in-one, fast. |
| **Formatting** | Biome | Prettier is slower. Biome formats and lints in one pass. |
| **Type Checking** | svelte-check + tsc | Built-in. Essential for catching errors. |
| **Dead Code** | Knip | Manual review misses things. Knip finds unused exports, deps, files. |

---

## Dev Experience

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Component Dev** | Histoire | Storybook is slow, complex config. Histoire is Vite-native, lighter, faster. |
| **i18n** | Paraglide | i18next has runtime overhead. Paraglide is compile-time, type-safe. |
| **Env Vars** | @t3-oss/env-core | dotenv doesn't validate. T3 env provides type-safe, validated env vars. |

---

## Production

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Logging** | Pino | Winston is slower. Pino is the fastest Node.js logger. |
| **Errors** | Sentry | Self-hosted is complex. Sentry has best Svelte integration. |
| **Deployment** | Railway / Vercel | Heroku is expensive; AWS is complex. Railway is simple, fast deploys. |

---

## Services

> See `shared/SERVICES.md` for detailed comparisons.

| Category | Primary | Notes |
|----------|---------|-------|
| **Hosting** | Railway | Or Cloudflare Pages for static/edge. |
| **Database** | Supabase | Or Neon for pure Postgres with branching. |
| **Search** | Meilisearch | Self-host, or use Meilisearch Cloud. |
| **Email** | Resend | Works great with React Email. |
| **Auth** | Better Auth | Self-hosted, TypeScript-first. |
| **Analytics** | Umami | Privacy-first, self-hosted, GDPR-friendly. |
| **Payments** | Stripe | Industry standard. LemonSqueezy if you need MoR. |

---

## Desktop Distribution (when needed)

| Category | Choice | When to Use |
|----------|--------|-------------|
| **Desktop App** | Tauri | When you need to ship a native desktop app. Smaller than Electron, Rust backend. |

> **Note**: Tauri is powerful but adds significant complexity. Only use if you actually need desktop distribution. Most apps should stay web-only.

---

## Infrastructure (add when needed)

| Category | Choice | Notes |
|----------|--------|-------|
| **Containers** | Docker | Dockerfile + docker-compose for local dev. |
| **IaC** | Pulumi | Uses TypeScript for infrastructure. No HCL to learn. |

### Documentation (add later, not at start)

| Category | Choice | Notes |
|----------|--------|-------|
| **Docs** | VitePress or Starlight | Modern, fast, Vite-based. Add only when you need public docs. |

---

## Version Requirements

```json
{
  "bun": ">=1.0.0",
  "svelte": ">=5.0.0",
  "sveltekit": ">=2.0.0",
  "astro": ">=4.0.0",
  "tailwindcss": ">=4.0.0",
  "drizzle-orm": ">=0.39.0",
  "biome": ">=1.9.0"
}
```

## Critical Notes

### SvelteKit
1. **Bun Adapter**: Use `svelte-adapter-bun` v1.0+ (recently rewritten, actively maintained)
2. **Tailwind v4**: Plugin order matters - `tailwindcss()` BEFORE `sveltekit()` in vite.config
3. **Dev Server**: Run with `bun --bun run dev` to use Bun runtime (not Node fallback)
4. **Svelte 5**: Uses runes (`$state`, `$derived`, `$effect`) - not legacy `$:` syntax

### Astro
1. **Content Collections**: Define schemas in `src/content/config.ts` with Zod
2. **Islands**: Use `client:load`, `client:idle`, `client:visible` directives for interactive components
3. **Static vs SSR**: Use `export const prerender = true/false` per-page, or set `output: 'static'|'server'|'hybrid'` in config
4. **Svelte in Astro**: Add `@astrojs/svelte` integration for interactive islands

### General
5. **Start minimal**: Don't add DuckDB, Tauri, or analytics until you need them

## Quick Reference: What to Install When

### SvelteKit Projects
| Project Type | Core Dependencies |
|-------------|-------------------|
| Landing Page | `sveltekit`, `tailwindcss`, `biome` |
| Web App | add `drizzle-orm`, `better-auth`, `superforms`, `zod` |
| + Email | add `resend`, `react-email` |
| + Search | add `meilisearch` |
| + Analytics | add `@umami/node` (or script tag) |
| + Rich Data Viz | add `layerchart` |
| + Client Analytics | add `duckdb-wasm` (rare) |
| Desktop App | add `tauri` (only if needed) |
| SaaS | add `stripe` |

### Astro Projects
| Project Type | Core Dependencies |
|-------------|-------------------|
| Blog / Portfolio | `astro`, `@astrojs/mdx`, `@astrojs/sitemap`, `tailwindcss`, `biome` |
| + Interactive UI | add `@astrojs/svelte`, `svelte` |
| + RSS Feed | add `@astrojs/rss` |
| + Image Optimization | add `sharp` (usually included) |
| + Search | add `pagefind` (static) or `meilisearch` (dynamic) |
| + CMS | add `@astrojs/db` or integrate with headless CMS |
| Docs Site | use Starlight (`@astrojs/starlight`) |

### Deployment Adapters
| Target | SvelteKit | Astro |
|--------|-----------|-------|
| Cloudflare | `@sveltejs/adapter-cloudflare` | `@astrojs/cloudflare` |
| Vercel | `@sveltejs/adapter-vercel` | `@astrojs/vercel` |
| Node/Bun | `svelte-adapter-bun` | `@astrojs/node` |
| Static | `@sveltejs/adapter-static` | `output: 'static'` (default) |
