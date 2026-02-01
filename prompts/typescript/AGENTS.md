# AGENTS.md — TypeScript/SvelteKit

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Bun (not Node)
Framework:   SvelteKit 2 + Svelte 5 (runes)
Styling:     Tailwind CSS v4
Database:    Drizzle ORM + PostgreSQL
Auth:        Better Auth (or Lucia for lightweight)
Testing:     Vitest + Playwright
Linting:     Biome
Tasks:       Just
```

---

## Commands

```bash
# Development
bun --bun run dev          # Start dev server (uses Bun runtime)
bun run build              # Production build
bun run preview            # Preview production build

# Quality
bun run check              # TypeScript + Svelte type checking
bun run lint               # Biome lint
bun run format             # Biome format

# Testing
bun test                   # Unit tests (Vitest)
bun run test:e2e           # E2E tests (Playwright)

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
│   │   └── auth/         # Lucia auth setup
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

## Styling Patterns

### Tailwind Order

```
layout → spacing → sizing → colors → typography → effects
```

Example:
```html
<div class="flex items-center gap-4 p-4 w-full bg-gray-100 text-sm font-medium rounded-lg shadow-sm">
```

### Component Variants (class-variance-authority)

```typescript
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);
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

## Testing Patterns

### Unit Test

```typescript
// src/lib/utils/format.test.ts
import { describe, it, expect } from 'vitest';
import { formatDate } from './format';

describe('formatDate', () => {
  it('formats ISO date to readable string', () => {
    expect(formatDate('2024-01-15')).toBe('January 15, 2024');
  });

  it('handles invalid dates', () => {
    expect(formatDate('invalid')).toBe('Invalid date');
  });
});
```

### Component Test

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

## Error Handling

### Custom Errors

```typescript
// src/lib/errors.ts
export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
  }
}

export class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}
```

### API Error Handler

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

## File Naming

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `Button.svelte`, `UserCard.svelte` |
| Routes | lowercase | `+page.svelte`, `+server.ts` |
| Utilities | camelCase | `formatDate.ts`, `useDebounce.ts` |
| Types | PascalCase | `User.ts`, `ApiResponse.ts` |
| Constants | SCREAMING_SNAKE | `API_BASE_URL`, `MAX_RETRIES` |

---

## Git Conventions

### Commit Messages

```
type(scope): description

feat(auth): add OAuth2 login flow
fix(api): handle null response from external service
refactor(db): migrate to Drizzle ORM
test(utils): add formatDate edge cases
docs(readme): update installation steps
chore(deps): bump svelte to 5.0.0
```

### Branch Names

```
feature/auth-oauth2
fix/api-null-response
refactor/db-drizzle
```

---

## Agent Output Rules

1. **All artifacts go in `.agents/`** — Never create random files in project root
2. **Date-prefix plans** — `YYYY-MM-DD-feature-name.md`
3. **Update .agents/README.md** — Keep index of all agent-generated files
4. **Clean working files** — Delete when no longer needed
5. **Architecture decisions** — Go in `.decisions/adr/`, not `.agents/`

---

## Critical Rules

### Always

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`) — never legacy `$:` syntax
- Run `bun run check` before committing
- Use Zod for all external data validation
- Handle loading and error states in UI
- Use `+page.server.ts` for data that needs auth

### Never

- Use `any` type — use `unknown` and narrow
- Skip error handling on async operations
- Commit `.env` files — use `.env.example`
- Use `console.log` in production code — use Pino logger
- Mutate props directly — derive new values

### Ask First

- Adding new dependencies
- Changing database schema
- Modifying auth flow
- Deleting files
