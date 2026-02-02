# Astro 4+

---

## Quick Reference

```yaml
Framework:   Astro 4+
UI:          Astro components (+ Svelte for islands)
Content:     Content Collections (MDX/Markdown)
```

---

## Commands

```bash
# Development
bun run dev                # Start dev server (localhost:4321)
bun run build              # Build for production (includes type check)
bun run preview            # Preview production build locally

# Quality
bun run astro check        # TypeScript + Astro type checking

# Deployment (Cloudflare example)
bun run deploy             # Build and deploy to Cloudflare Pages
```

---

## Project Structure

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

## File Naming (Astro)

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `Card.astro` |
| Routes | lowercase | `index.astro`, `[...slug].astro` |
| Content | lowercase-kebab | `my-first-post.mdx` |

---

## Critical Rules (Astro)

### Always

- Define content collection schemas in `src/content/config.ts`
- Use `export const prerender = true` for static pages in hybrid mode
- Prefer `.astro` components; use Svelte only for interactive islands

### Never

- Ship unnecessary JavaScript — Astro is static-first

### Ask First

- Changing content collection schemas
