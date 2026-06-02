# SvelteKit

> Curated taste, not mandate — patterns for SvelteKit 2 + Svelte 5 on Bun.

## Stack at a glance

```yaml
Framework:   SvelteKit 2 + Svelte 5 (runes)
Runtime:     Bun (svelte-adapter-bun for production)
Database:    Drizzle ORM + PostgreSQL
Auth:        Better Auth (or Lucia for lightweight)
Forms:       Superforms + Zod
Components:  shadcn-svelte + Bits UI
```

## Svelte 5 runes — not legacy syntax

Use runes, never the Svelte 4 reactive forms:

- `$state()` for reactive state — NOT bare `let x` reactivity.
- `$derived()` for computed values — NOT `$: x = ...`.
- `$effect()` for side effects — NOT `$: { ... }`.
- `$props()` for component props — NOT `export let`.
- `$bindable()` for two-way binding props.

```svelte
<script lang="ts">
  let count = $state(0);
  let doubled = $derived(count * 2);

  $effect(() => {
    console.log(count);
  });
</script>
```

### Typed props with `$props()`

```svelte
<script lang="ts">
  let {
    variant = 'default',
    disabled = false,
    class: className = '',
    children,
  }: {
    variant?: 'default' | 'outline';
    disabled?: boolean;
    class?: string;
    children?: import('svelte').Snippet;
  } = $props();
</script>
```

## Data loading

- `+page.server.ts` for data that needs auth or DB access; read auth off `locals`.
- `+page.ts` for public data or client-side fetching.
- Return plain objects from `load` — SvelteKit serializes them.

```typescript
// +page.server.ts
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params }) => {
  const user = locals.user; // set in hooks
  const posts = await db.query.posts.findMany();
  return { posts, user };
};
```

## Form actions

Use Superforms + Zod for form handling with progressive enhancement.

```typescript
// +page.server.ts
import type { Actions } from './$types';
import { fail } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export const actions: Actions = {
  default: async ({ request }) => {
    const form = await superValidate(request, zod(schema));
    if (!form.valid) return fail(400, { form });
    // process...
    return { form };
  },
};
```

## Database (Drizzle)

- One table per file in `src/lib/server/db/schema/`.
- Use `drizzle-zod` to generate Zod schemas from tables — single source of truth.
- Transactions: `await db.transaction(async (tx) => { ... })`.

## Project layout

```
src/
├── lib/
│   ├── components/ui/   # shadcn-svelte components
│   ├── server/db/       # Drizzle schema + queries
│   ├── server/auth/     # Auth setup
│   └── utils/           # Shared utilities
└── routes/              # File-based routing
    ├── +layout.svelte
    ├── +page.svelte
    └── api/             # API routes (+server.ts)
```

## Commands

```bash
bun --bun run dev          # Dev server with Bun runtime
bun run build && bun run preview
bun run check              # Type check
bun run lint               # Biome lint
bun test                   # Unit tests
bun run db:generate        # Generate migration
bun run db:migrate         # Run migrations
bun run db:studio          # Open Drizzle Studio
```

## Critical / common mistakes

- **Tailwind plugin order:** `tailwindcss()` BEFORE `sveltekit()` in `vite.config`.
- **Production adapter:** use `svelte-adapter-bun` (v1.0+, actively maintained).
- Always run dev with `--bun` (`bun --bun run dev`), not the Node runtime.
- Use `{@render children?.()}` with snippets — NOT `<slot>`.
- Use `onclick` (lowercase, no colon) — NOT `on:click`.

## See also

- [../README.md](../README.md) — TypeScript stack selection and idioms
- [astro.md](astro.md) — content sites and islands
- [../../../engineering-philosophy.md](../../../engineering-philosophy.md) — universal code-health principles
