# AGENTS.md — TypeScript (Base)

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Bun (not Node)
Styling:     Tailwind CSS v4
Logging:     pino (structured JSON)
Testing:     Vitest (+ Playwright for interactive apps)
Profiling:   Lighthouse CLI
Linting:     Biome
Tasks:       Just
```

> **Testing Philosophy**: Match testing to complexity. Static content sites (blogs, portfolios) need minimal testing — if it builds, it works. Save E2E testing for apps with auth, forms, and complex interactions.

---

## Commands (Shared)

```bash
# Quality
bun run check              # TypeScript type checking
bun run lint               # Biome lint
bun run format             # Biome format

# Testing
bun test                   # Unit tests (Vitest)
bun run test:e2e           # E2E tests (Playwright)
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

---

## Logging (pino)

```typescript
// src/lib/server/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  ...(process.env.NODE_ENV === 'development' && {
    transport: {
      target: 'pino-pretty',
      options: { colorize: true },
    },
  }),
});

// Usage
logger.info({ userId: user.id }, 'user logged in');
logger.error({ err, requestId }, 'request failed');
logger.debug({ query, params }, 'database query');

// Child logger with context
const reqLogger = logger.child({ requestId: crypto.randomUUID() });
reqLogger.info('handling request');
```

### Request Logging Middleware

```typescript
// SvelteKit hook example
import { logger } from '$lib/server/logger';

export const handle = async ({ event, resolve }) => {
  const requestId = crypto.randomUUID();
  const start = performance.now();

  const response = await resolve(event);

  logger.info({
    requestId,
    method: event.request.method,
    path: event.url.pathname,
    status: response.status,
    duration: Math.round(performance.now() - start),
  }, 'request completed');

  return response;
};
```

---

## Performance Profiling

### Lighthouse CLI

```bash
# Install
bun add -d lighthouse

# Run audit (requires built app)
bun run build && bun run preview &
npx lighthouse http://localhost:4173 --output=html --output-path=./lighthouse-report.html

# CI-friendly JSON output
npx lighthouse http://localhost:4173 --output=json --output-path=./lighthouse.json

# Specific categories
npx lighthouse http://localhost:4173 --only-categories=performance,accessibility
```

### Performance Budgets

```typescript
// lighthouse.config.js
export default {
  assertions: {
    'categories:performance': ['error', { minScore: 0.9 }],
    'categories:accessibility': ['error', { minScore: 0.9 }],
    'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
    'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
    'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
  },
};
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

---

## File Naming

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `Button.svelte`, `Card.astro` |
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

- Run type checking before committing (`bun run check`)
- Use Zod for all external data validation
- Handle loading and error states in UI

### Never

- Use `any` type — use `unknown` and narrow
- Skip error handling on async operations
- Commit `.env` files — use `.env.example`
- Use `console.log` in production code — use pino
- Mutate props directly — derive new values

### Ask First

- Adding new dependencies
- Changing database schema
- Modifying auth flow
- Deleting files
