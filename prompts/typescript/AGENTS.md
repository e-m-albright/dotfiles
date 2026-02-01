# AGENTS.md — TypeScript

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Bun (not Node)
Framework:   SvelteKit 2 | Astro 4+ (detect from config)
UI:          Svelte 5 (runes) | Astro components
Styling:     Tailwind CSS v4
Database:    Drizzle ORM + PostgreSQL (when needed)
Auth:        Better Auth (or Lucia for lightweight)
Testing:     Vitest + Playwright
Linting:     Biome
Tasks:       Just
```

> **Framework Detection**: Check for `svelte.config.js` (SvelteKit) or `astro.config.mjs` (Astro) to determine which patterns apply.

---

## Commands

### SvelteKit Projects

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

### Astro Projects

```bash
# Development
bun run dev                # Start dev server (localhost:4321)
bun run build              # Build for production (includes type check)
bun run preview            # Preview production build locally

# Quality
bun run astro check        # TypeScript + Astro type checking
bun run lint               # Biome lint (or ESLint if configured)
bun run format             # Biome format

# Deployment (Cloudflare example)
bun run deploy             # Build and deploy to Cloudflare Pages
```

---

## Project Structure

### SvelteKit

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

### Astro

```
src/
├── components/           # Astro/Svelte components
│   └── ui/              # Reusable UI components
├── content/             # Content collections
│   ├── config.ts        # Collection schemas (Zod)
│   ├── blog/            # Blog posts (MDX/Markdown)
│   └── projects/        # Other collections
├── layouts/             # Page layouts
│   └── Layout.astro     # Base layout
├── pages/               # File-based routing
│   ├── index.astro      # Home page
│   ├── blog/
│   │   ├── index.astro  # Blog listing
│   │   └── [...slug].astro  # Dynamic post pages
│   └── api/             # API routes (.ts files)
├── lib/                 # Shared utilities
│   └── utils.ts
└── styles/              # Global styles
    └── global.css
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

## Astro Patterns

### Content Collections

```typescript
// src/content/config.ts
import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    draft: z.boolean().optional(),
  }),
});

export const collections = { blog };
```

### Querying Content

```astro
---
import { getCollection, getEntry } from 'astro:content';

// Get all non-draft posts, sorted by date
const posts = (await getCollection('blog'))
  .filter(post => !post.data.draft)
  .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

// Get single entry
const post = await getEntry('blog', 'my-post');
const { Content } = await post.render();
---

<Content />
```

### Static Paths (Dynamic Routes)

```astro
---
// src/pages/blog/[...slug].astro
import { getCollection } from 'astro:content';

export const prerender = true;

export async function getStaticPaths() {
  const posts = await getCollection('blog');
  return posts.map(post => ({
    params: { slug: post.slug },
    props: { post },
  }));
}

const { post } = Astro.props;
const { Content } = await post.render();
---
```

### Islands (Interactive Components)

```astro
---
import Counter from '@components/Counter.svelte';
---

<!-- No JS shipped -->
<p>Static content</p>

<!-- Hydrate strategies -->
<Counter client:load />      <!-- Immediate -->
<Counter client:idle />      <!-- When browser idle -->
<Counter client:visible />   <!-- When in viewport -->
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
| Components | PascalCase | `Button.svelte`, `Card.astro` |
| Routes (SvelteKit) | lowercase | `+page.svelte`, `+server.ts` |
| Routes (Astro) | lowercase | `index.astro`, `[...slug].astro` |
| Content | lowercase-kebab | `my-first-post.mdx` |
| Utilities | camelCase | `formatDate.ts`, `readingTime.ts` |
| Types | PascalCase | `User.ts`, `ApiResponse.ts` |
| Constants | SCREAMING_SNAKE | `SITE_URL`, `MAX_POSTS_PER_PAGE` |

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
5. **Architecture decisions** — Go in `.architecture/adr/`, not `.agents/`

---

## Critical Rules

### Always

- Run type checking before committing (`bun run check` or `astro check`)
- Use Zod for all external data validation
- Handle loading and error states in UI

**SvelteKit:**
- Use Svelte 5 runes (`$state`, `$derived`, `$effect`) — never legacy `$:` syntax
- Use `+page.server.ts` for data that needs auth

**Astro:**
- Define content collection schemas in `src/content/config.ts`
- Use `export const prerender = true` for static pages in hybrid mode
- Prefer `.astro` components; use Svelte only for interactive islands

### Never

- Use `any` type — use `unknown` and narrow
- Skip error handling on async operations
- Commit `.env` files — use `.env.example`
- Use `console.log` in production code — use structured logger
- Mutate props directly — derive new values

### Ask First

- Adding new dependencies
- Changing database schema
- Modifying auth flow
- Changing content collection schemas
- Deleting files
