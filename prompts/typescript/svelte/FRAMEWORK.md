# SvelteKit + Svelte 5

---

## Quick Reference

```yaml
Framework:   SvelteKit 2
UI:          Svelte 5 (runes)
Database:    Drizzle ORM + PostgreSQL (when needed)
Auth:        Better Auth (or Lucia for lightweight)
```

---

## Commands

```bash
# Development
bun --bun run dev          # Start dev server (uses Bun runtime)
bun run build              # Production build
bun run preview            # Preview production build

# Database
bun run db:generate        # Generate migrations
bun run db:migrate         # Run migrations
bun run db:studio          # Open Drizzle Studio
```

---

## Project Structure

```
src/
├── lib/                   # Shared code (aliased as $lib)
│   ├── components/        # Svelte components
│   │   └── ui/           # shadcn-svelte components
│   ├── server/           # Server-only code
│   │   ├── db/           # Drizzle schema + queries
│   │   └── auth/         # Auth setup
│   └── utils/            # Shared utilities
├── routes/               # SvelteKit file-based routing
│   ├── +layout.svelte    # Root layout
│   ├── +page.svelte      # Home page
│   └── api/              # API routes (+server.ts files)
├── app.html              # HTML template
└── app.css               # Global styles (Tailwind imports)
```

---

## Svelte 5 Patterns

### State (Runes)

```svelte
<script lang="ts">
  // Reactive state
  let count = $state(0);

  // Derived values (computed)
  let doubled = $derived(count * 2);

  // Props with defaults
  let { title = 'Default', onClick }: { title?: string; onClick: () => void } = $props();

  // Two-way binding prop
  let { value = $bindable() }: { value: string } = $props();

  // Side effects
  $effect(() => {
    console.log(`Count changed to ${count}`);
    // Cleanup returned function runs on destroy or re-run
    return () => console.log('Cleaning up');
  });
</script>
```

### Component Structure

```svelte
<!-- 1. Script (logic) -->
<script lang="ts">
  // Types first
  interface Props { ... }

  // Props
  let { ... }: Props = $props();

  // State
  let value = $state(...);

  // Derived
  let computed = $derived(...);

  // Effects
  $effect(() => { ... });

  // Functions
  function handleClick() { ... }
</script>

<!-- 2. Markup -->
<div class="...">
  ...
</div>

<!-- 3. Styles (scoped, prefer Tailwind) -->
<style>
  /* Only for complex animations or :global overrides */
</style>
```

### Data Loading

```typescript
// +page.server.ts
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params }) => {
  const user = locals.user;  // From hooks
  const data = await db.query.posts.findMany({
    where: eq(posts.authorId, params.id)
  });

  return { posts: data };
};
```

### Form Actions

```typescript
// +page.server.ts
import type { Actions } from './$types';
import { fail, redirect } from '@sveltejs/kit';
import { superValidate, message } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { schema } from './schema';

export const actions: Actions = {
  default: async ({ request }) => {
    const form = await superValidate(request, zod(schema));

    if (!form.valid) {
      return fail(400, { form });
    }

    // Process form...

    return message(form, 'Success!');
  }
};
```

---

## Database Patterns

### Schema Definition

```typescript
// src/lib/server/db/schema.ts
import { pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  name: text('name'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Auto-generate Zod schemas
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
```

### Queries

```typescript
// src/lib/server/db/queries.ts
import { db } from './client';
import { users } from './schema';
import { eq } from 'drizzle-orm';

export async function getUserById(id: string) {
  return db.query.users.findFirst({
    where: eq(users.id, id),
  });
}

export async function createUser(data: typeof users.$inferInsert) {
  const [user] = await db.insert(users).values(data).returning();
  return user;
}
```

---

## Component Test

```typescript
// src/lib/components/Button.test.ts
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import Button from './Button.svelte';

it('calls onClick when clicked', async () => {
  const user = userEvent.setup();
  const onClick = vi.fn();

  render(Button, { props: { onClick, children: 'Click me' } });

  await user.click(screen.getByRole('button'));

  expect(onClick).toHaveBeenCalledOnce();
});
```

---

## API Error Handler

```typescript
// src/routes/api/[...path]/+server.ts
import { json } from '@sveltejs/kit';
import { AppError } from '$lib/errors';

export function handleApiError(error: unknown) {
  if (error instanceof AppError) {
    return json(
      { error: { code: error.code, message: error.message } },
      { status: error.statusCode }
    );
  }

  console.error('Unexpected error:', error);
  return json(
    { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' } },
    { status: 500 }
  );
}
```

---

## File Naming (SvelteKit)

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `Button.svelte` |
| Routes | lowercase | `+page.svelte`, `+server.ts` |

---

## Critical Rules (SvelteKit)

### Always

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`) — never legacy `$:` syntax
- Use `+page.server.ts` for data that needs auth

### Never

- Use legacy Svelte 4 reactive syntax (`$:`, `export let`)

### Ask First

- Changing content collection schemas
