# TypeScript Style Guide

## TypeScript

### Types over Interfaces (for most cases)

```typescript
// Prefer type for unions, intersections, mapped types
type Status = 'pending' | 'active' | 'completed';
type ApiResponse<T> = { data: T; error: null } | { data: null; error: string };

// Use interface for extendable shapes or class implementations
interface UserRepository {
  findById(id: string): Promise<User | null>;
  create(data: CreateUserInput): Promise<User>;
}
```

### Strict Null Handling

```typescript
// Bad: relies on truthy check
function getName(user: User | null) {
  return user?.name || 'Anonymous';  // Empty string becomes 'Anonymous'
}

// Good: explicit null check
function getName(user: User | null) {
  return user?.name ?? 'Anonymous';
}
```

### Discriminated Unions for State

```typescript
// Bad: optional properties create invalid states
type ApiState = {
  loading?: boolean;
  data?: Data;
  error?: Error;
};

// Good: discriminated union prevents invalid states
type ApiState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Data }
  | { status: 'error'; error: Error };
```

### Const Assertions

```typescript
// For immutable arrays/objects
const ROUTES = ['home', 'about', 'contact'] as const;
type Route = typeof ROUTES[number]; // 'home' | 'about' | 'contact'

const CONFIG = {
  apiUrl: 'https://api.example.com',
  timeout: 5000,
} as const;
```

### Generic Constraints

```typescript
// Bad: too permissive
function merge<T>(a: T, b: T): T { ... }

// Good: constrained to objects
function merge<T extends Record<string, unknown>>(a: T, b: Partial<T>): T {
  return { ...a, ...b };
}
```

---

## Svelte 5

### Runes Usage

```svelte
<script lang="ts">
  // State: simple reactive values
  let count = $state(0);

  // State: objects (automatically deep reactive)
  let user = $state({ name: '', email: '' });

  // Derived: computed values (memoized)
  let isValid = $derived(user.name.length > 0 && user.email.includes('@'));

  // Effect: side effects that track dependencies
  $effect(() => {
    document.title = `Count: ${count}`;
  });

  // Effect with cleanup
  $effect(() => {
    const interval = setInterval(() => count++, 1000);
    return () => clearInterval(interval);
  });
</script>
```

### Props Pattern

```svelte
<script lang="ts">
  // Destructure with defaults
  let {
    variant = 'default',
    size = 'md',
    disabled = false,
    class: className = '',  // Rename reserved word
    children,               // Slot content
    ...rest                 // Spread remaining
  }: {
    variant?: 'default' | 'outline' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
    class?: string;
    children?: import('svelte').Snippet;
  } & HTMLButtonAttributes = $props();
</script>

<button
  class={cn(buttonVariants({ variant, size }), className)}
  {disabled}
  {...rest}
>
  {@render children?.()}
</button>
```

### Snippets (replaces slots)

```svelte
<!-- Parent -->
<Card>
  {#snippet header()}
    <h2>Card Title</h2>
  {/snippet}

  {#snippet footer()}
    <Button>Save</Button>
  {/snippet}

  <p>Card content goes here.</p>
</Card>

<!-- Card.svelte -->
<script lang="ts">
  let { header, footer, children }: {
    header?: import('svelte').Snippet;
    footer?: import('svelte').Snippet;
    children?: import('svelte').Snippet;
  } = $props();
</script>

<div class="card">
  {#if header}
    <div class="card-header">{@render header()}</div>
  {/if}

  <div class="card-body">{@render children?.()}</div>

  {#if footer}
    <div class="card-footer">{@render footer()}</div>
  {/if}
</div>
```

### Event Handlers

```svelte
<script lang="ts">
  // Callback props (preferred)
  let { onClick }: { onClick?: (event: MouseEvent) => void } = $props();

  // Internal handlers
  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    // ...
  }
</script>

<form onsubmit={handleSubmit}>
  <button onclick={onClick}>Click</button>
</form>
```

---

## Tailwind CSS v4

### Class Order

Follow consistent ordering for readability:

```
1. Layout       (display, position, flex, grid)
2. Spacing      (margin, padding, gap)
3. Sizing       (width, height, min/max)
4. Colors       (background, text, border colors)
5. Typography   (font, text alignment)
6. Effects      (shadow, opacity, transform)
7. States       (hover:, focus:, dark:)
```

### Responsive Design

```html
<!-- Mobile-first: base → sm → md → lg → xl -->
<div class="
  flex flex-col gap-4 p-4
  md:flex-row md:gap-8 md:p-8
  lg:p-12
">
```

### Dark Mode

```html
<!-- Use dark: variant -->
<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">

<!-- CSS custom properties for theming -->
<div class="bg-background text-foreground">
```

### Avoiding Utility Soup

```svelte
<!-- Bad: too many classes, hard to read -->
<button class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">

<!-- Good: extract to component with cva -->
<Button variant="default" size="default">Click</Button>
```

---

## Drizzle Patterns

### Schema Organization

```typescript
// schema/index.ts - re-exports all tables
export * from './users';
export * from './posts';
export * from './comments';

// schema/users.ts - single table per file
import { pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';
import { posts } from './posts';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
}));
```

### Query Patterns

```typescript
// Simple select
const user = await db.query.users.findFirst({
  where: eq(users.id, userId),
});

// With relations
const userWithPosts = await db.query.users.findFirst({
  where: eq(users.id, userId),
  with: {
    posts: {
      orderBy: desc(posts.createdAt),
      limit: 10,
    },
  },
});

// Complex query
const results = await db
  .select({
    id: users.id,
    email: users.email,
    postCount: count(posts.id),
  })
  .from(users)
  .leftJoin(posts, eq(users.id, posts.authorId))
  .groupBy(users.id)
  .having(gt(count(posts.id), 5));
```

### Transaction Pattern

```typescript
await db.transaction(async (tx) => {
  const [user] = await tx.insert(users).values({ email }).returning();
  await tx.insert(profiles).values({ userId: user.id, name });
  return user;
});
```

---

## File Organization

### Feature-Based Structure

```
src/lib/
├── features/
│   ├── auth/
│   │   ├── components/
│   │   │   ├── LoginForm.svelte
│   │   │   └── SignupForm.svelte
│   │   ├── server/
│   │   │   ├── lucia.ts
│   │   │   └── guards.ts
│   │   └── schemas.ts
│   └── posts/
│       ├── components/
│       │   ├── PostCard.svelte
│       │   └── PostList.svelte
│       ├── server/
│       │   └── queries.ts
│       └── schemas.ts
├── components/
│   └── ui/              # shadcn-svelte components
└── server/
    └── db/
        ├── client.ts
        └── schema/
```

### Import Order

```typescript
// 1. Svelte/SvelteKit
import { onMount } from 'svelte';
import { goto } from '$app/navigation';

// 2. External packages
import { z } from 'zod';
import { eq } from 'drizzle-orm';

// 3. Internal aliases ($lib)
import { db } from '$lib/server/db';
import { Button } from '$lib/components/ui';

// 4. Relative imports
import { formatDate } from './utils';
import type { Post } from './types';
```

---

## Error Messages

### User-Facing

```typescript
// Bad: technical jargon
throw new Error('ECONNREFUSED 127.0.0.1:5432');

// Good: helpful message
throw new AppError(
  'Unable to connect to the database. Please try again later.',
  'DATABASE_CONNECTION_ERROR'
);
```

### Developer-Facing (Logs)

```typescript
// Include context for debugging
logger.error('Database connection failed', {
  host: config.dbHost,
  port: config.dbPort,
  error: error.message,
  stack: error.stack,
  requestId: locals.requestId,
});
```
