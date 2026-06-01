# TypeScript

> Curated taste, not mandate — read this to derive per-project choices.

## Selection (pick / avoid / by phase)

Selection is *what* to reach for. Idioms below are *how* to use them. Detect the existing stack from project files before applying any of this — never switch package managers, linters, or frameworks in a project that already chose otherwise.

### Phase 1 — every project

| Category | Pick | Avoid (why) |
|----------|------|-------------|
| Runtime | **Bun** | Node.js (slower), Deno (ecosystem gaps) |
| Lint + format | **Biome** (one tool) | ESLint + Prettier (slow, config hell) |
| Task runner | **Just** | npm scripts (limited), Make (arcane) |
| Git hooks | **Lefthook** | Husky (slower, JS-based) |
| Styling | **Tailwind CSS v4** | CSS-in-JS (runtime cost), Sass (verbose) |

### Phase 2 — when needed

| Need | Pick | Avoid (why) |
|------|------|-------------|
| Full-stack app | **SvelteKit 2** | Next.js (React bloat, Vercel-coupled), Nuxt (Vue) |
| Content site | **Astro** | Gatsby (stagnant), Hugo (non-JS) |
| UI components | **shadcn-svelte + Bits UI** | Chakra/MUI (React-only, heavy) |
| ORM | **Drizzle** | Prisma (Bun cold-start issues, slow) |
| Database | **PostgreSQL** | SQLite (lacks concurrent writes) |
| Auth | **Better Auth** (Lucia for lightweight) | Auth0 (complex), NextAuth (React-only) |
| Forms | **Superforms + Zod** | Formik (React-only) |
| Validation | **Zod** | Yup (worse TS inference) |
| Data fetching | **TanStack Query** | SWR (React-only) |
| Charts | **LayerChart** | Recharts (React-only), Chart.js (limited) |
| i18n (SvelteKit) | **Paraglide JS 2.0** | i18next (runtime overhead) |

### Phase 3 — at scale

| Need | Pick | Notes |
|------|------|-------|
| Desktop app | **Tauri** | Only when you need native distribution |
| Client analytics | **DuckDB-WASM** | Heavy client-side data processing |
| Observability | **OpenTelemetry** | When 2+ services call each other |
| Monorepo build | **Turborepo** | Simplest, Vercel-maintained. Over nx (plugin-heavy), moon (Rust-based) |
| Dead code | **Knip** | Finds unused exports, deps, files |
| Component dev | **Histoire** | Vite-native; lighter than Storybook |
| Docs site | **Starlight** (Astro) | Best docs DX in the ecosystem |

### Don't install

- **Prettier / ESLint** — Biome does both.
- **Storybook** — Histoire is lighter and Vite-native.
- **Next.js** — Vercel-coupled, complexity creep.

### Version floors

Bun >=1.0, Svelte >=5.0, SvelteKit >=2.0, Astro >=4.0, Tailwind >=4.0, Biome >=1.9.

## Idioms

### Runtime & package management

- **Bun** is the runtime unless compatibility forces Node.
- Detect the lockfile (`bun.lock`, `pnpm-lock.yaml`, …) and use the matching package manager. Never switch managers in an existing project.

### Formatting & linting

- Use **Biome** when `biome.json` is present. Don't introduce Prettier/ESLint alongside it.
- With no Biome config, fall back to whatever the repo already uses. Don't add new lint rules or config files without asking.

### Types

- Prefer `type` for unions, intersections, and mapped types; `interface` for extendable shapes.
- Model state with **discriminated unions** — not `{ loading?: boolean; data?: T; error?: Error }`.
- Use `satisfies` for narrowing when it improves readability.
- Use `as const` for immutable arrays/objects.
- Use `??` (nullish coalescing) for defaults, not `||` — `||` swallows `''` and `0`.
- Never `any`. If you're tempted, the type design is wrong: use `unknown` and narrow.

### Code

- **Named exports** over default exports.
- Barrel files (`index.ts`) for re-exports only — no logic. Don't re-export types just for convenience; import from the source.
- **Zod** for all external-data validation.
- **`pino`** for logging — never `console.log` in production.
- Don't `try/catch` around code that can't throw — only wrap genuinely fallible operations. Never skip error handling on async work; unhandled rejections crash the process.
- Don't mutate props — derive new values.

### Styling

- **Tailwind CSS v4**. Class order: layout → spacing → sizing → colors → typography → effects.
- Extract repeated class sets into components with `cva` (class-variance-authority).

### Always

- Run type checking before committing (`bun run check`).
- Handle loading and error states in UI components.

## Code patterns

### Discriminated union for async state

```typescript
type State<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };
```

### CVA component variants

```typescript
import { cva, type VariantProps } from 'class-variance-authority';

export const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        outline: 'border border-input hover:bg-accent',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  }
);

export type ButtonVariants = VariantProps<typeof buttonVariants>;
```

### Drizzle schema as single source of truth

```typescript
import { pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Auto-generate Zod schemas from the table — don't hand-maintain a parallel schema.
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
```

## Project layout

- One Drizzle table per file in `src/lib/server/db/schema/`.
- Generate Zod schemas from Drizzle tables (`drizzle-zod`) rather than maintaining both.
- Transactions: `await db.transaction(async (tx) => { ... })`.

## Ask first

- Adding new dependencies.
- Changing database schema.
- Modifying auth flow.
- Deleting files.

## See also

- [frameworks/sveltekit.md](frameworks/sveltekit.md) — SvelteKit 2 + Svelte 5 patterns
- [frameworks/astro.md](frameworks/astro.md) — Astro content sites and islands
- [../../docs/engineering-philosophy.md](../engineering-philosophy.md) — universal code-health principles
