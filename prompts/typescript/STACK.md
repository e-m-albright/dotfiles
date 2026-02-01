# TypeScript Stack

**Philosophy**: Modern, type-safe, full-stack web development with maximum DX.

## Runtime & Tooling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Runtime** | Bun | Node.js is slower; Deno has ecosystem gaps. Bun is 3-4x faster, native TypeScript, built-in test runner. |
| **Package Manager** | Bun | pnpm is good but Bun is faster and eliminates tool sprawl. |
| **Linter/Formatter** | Biome | ESLint + Prettier is slow and requires config hell. Biome is 35x faster, single tool, Rust-based. |
| **Git Hooks** | Lefthook | Husky is slower, JS-based. Lefthook is Go-based, parallel execution, YAML config. |
| **Task Runner** | Just | npm scripts are limited; Make syntax is archaic. Just is readable, cross-platform, modern. |

## Framework & Build

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | SvelteKit 2 | Next.js is React (more boilerplate); Nuxt is Vue (less type-safe). SvelteKit is simpler, faster, better DX. |
| **UI Framework** | Svelte 5 | React has hooks complexity; Vue has Options/Composition duality. Svelte 5 runes are intuitive and performant. |
| **Build** | Vite | Built into SvelteKit. Webpack is slow; Turbopack is React-only. |
| **Adapter** | svelte-adapter-bun | Native Bun integration for production. |

## State & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Server State** | TanStack Query (Svelte) | SWR is React-only. TanStack has better devtools, mutations, infinite queries. |
| **Client State** | Svelte 5 Runes | Built-in. Zustand/Jotai are React-centric; Svelte's reactivity is superior. |
| **Forms** | Superforms + Zod | Formik is React-only; react-hook-form is complex. Superforms is SvelteKit-native with progressive enhancement. |
| **Validation** | Zod | Yup has worse TypeScript inference. Zod is TS-first with excellent DX. |

## UI & Styling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Styling** | Tailwind CSS v4 | CSS-in-JS has runtime cost; Sass is verbose. Tailwind v4 is CSS-first, faster, smaller. |
| **Components** | shadcn-svelte + Bits UI | Chakra/MUI are heavy, React-only. shadcn is copy-paste, customizable, accessible via Bits UI. |
| **Charts** | LayerChart | Recharts is React-only; Chart.js lacks customization. LayerChart is Svelte-native, D3-powered. |
| **Animations** | Svelte transitions | Framer Motion is React-only. Svelte has excellent built-in transitions. |

## Database & Backend

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **ORM** | Drizzle | Prisma has Bun compatibility issues, slower cold starts. Drizzle is type-safe SQL, faster, lighter. |
| **Database** | PostgreSQL | SQLite lacks concurrent writes for production. Postgres is the industry standard. |
| **Migrations** | drizzle-kit | Prisma Migrate is slower. drizzle-kit generates clean SQL migrations. |
| **Schema Sync** | drizzle-zod | Generates Zod schemas from Drizzle tables. Single source of truth. |

## Auth

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Auth** | Lucia | NextAuth is React-focused; Auth.js is complex. Lucia is lightweight, framework-agnostic, well-documented. |
| **Alternative** | Better Auth | Newer option if Lucia doesn't fit. Both integrate well with Drizzle. |

## Testing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Unit** | Vitest | Jest is slower, needs more config. Vitest is Vite-native, faster, better DX. |
| **Component** | @testing-library/svelte | Enzyme is dead. Testing Library focuses on user behavior, not implementation. |
| **E2E** | Playwright | Cypress is slower, limited cross-browser. Playwright is faster, better debugging. |
| **Mocking** | MSW | Nock is Node-only. MSW works in browser and Node, intercepts at network level. |

## Code Quality

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Linting** | Biome | ESLint + plugins is slow. Biome is all-in-one, fast. |
| **Formatting** | Biome | Prettier is slower. Biome formats and lints in one pass. |
| **Type Checking** | svelte-check + tsc | Built-in. Essential for catching errors. |
| **Dead Code** | Knip | Manual review misses things. Knip finds unused exports, deps, files. |

## Dev Experience

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Component Dev** | Histoire | Storybook is slow, complex config. Histoire is Vite-native, lighter, faster. |
| **i18n** | Paraglide | i18next has runtime overhead. Paraglide is compile-time, type-safe. |
| **Env Vars** | @t3-oss/env-core | dotenv doesn't validate. T3 env provides type-safe, validated env vars. |

## Production

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Logging** | Pino | Winston is slower. Pino is the fastest Node.js logger. |
| **Errors** | Sentry | Self-hosted is complex. Sentry has best Svelte integration. |
| **Deployment** | Railway / Vercel | Heroku is expensive; AWS is complex. Railway is simple, fast deploys. |

---

## Version Requirements

```json
{
  "bun": ">=1.0.0",
  "svelte": ">=5.0.0",
  "sveltekit": ">=2.0.0",
  "tailwindcss": ">=4.0.0",
  "drizzle-orm": ">=0.39.0",
  "biome": ">=1.9.0"
}
```

## Critical Notes

1. **Bun Adapter**: Use `svelte-adapter-bun` v1.0+ (recently rewritten, actively maintained)
2. **Tailwind v4**: Plugin order matters - `tailwindcss()` BEFORE `sveltekit()` in vite.config
3. **Dev Server**: Run with `bun --bun run dev` to use Bun runtime (not Node fallback)
4. **Svelte 5**: Uses runes (`$state`, `$derived`, `$effect`) - not legacy `$:` syntax
