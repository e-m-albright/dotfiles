---
name: sveltekit-bun-stack
description: |
  Use this skill when working with SvelteKit 2 + Svelte 5 + Bun projects.
  Covers: Svelte 5 runes, SvelteKit routing, Drizzle ORM, Tailwind v4, shadcn-svelte.
---

# SvelteKit + Bun Stack

## When This Skill Applies

- Working with `.svelte` files
- SvelteKit routing (`+page.svelte`, `+server.ts`, etc.)
- Drizzle ORM schemas and queries
- Tailwind CSS styling
- shadcn-svelte or Bits UI components

## Critical Patterns

### Svelte 5 Runes (NOT legacy syntax)

```svelte
<!-- CORRECT: Svelte 5 runes -->
<script lang="ts">
  let count = $state(0);
  let doubled = $derived(count * 2);

  $effect(() => {
    console.log(count);
  });
</script>

<!-- WRONG: Legacy Svelte 4 syntax -->
<script>
  let count = 0;
  $: doubled = count * 2;  // DON'T USE THIS
</script>
```

### Props with $props()

```svelte
<script lang="ts">
  // Destructure with types and defaults
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

### SvelteKit Data Loading

```typescript
// +page.server.ts — Server-side data loading
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params }) => {
  // Access auth from hooks
  const user = locals.user;

  // Fetch data
  const data = await db.query.posts.findMany();

  // Return to page
  return { posts: data, user };
};
```

### SvelteKit Form Actions

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

    // Process...
    return { form };
  }
};
```

### Drizzle Schema

```typescript
import { pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Auto-generate Zod schemas
export const insertUserSchema = createInsertSchema(users);
```

### Tailwind + CVA Component

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
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);
```

## Commands

```bash
bun --bun run dev      # Dev server with Bun runtime
bun run check          # Type check
bun run lint           # Biome lint
bun test               # Unit tests
bun run db:generate    # Generate migration
bun run db:studio      # Open Drizzle Studio
```

## Common Mistakes to Avoid

1. **Using `$:` reactive declarations** — Use `$derived()` instead
2. **Using `let` for props** — Use `$props()` destructuring
3. **Using `<slot>`** — Use `{@render children?.()}` with snippets
4. **Using `on:click`** — Use `onclick` (lowercase, no colon)
5. **Running dev without `--bun`** — Always `bun --bun run dev`

## File Structure

```
src/
├── lib/
│   ├── components/ui/    # shadcn-svelte components
│   ├── server/db/        # Drizzle schema + queries
│   └── utils/            # Shared utilities
└── routes/               # SvelteKit pages
    ├── +layout.svelte
    ├── +page.svelte
    └── api/              # API routes
```
