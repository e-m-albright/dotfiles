# Astro

> Curated taste, not mandate — patterns for content-first Astro sites.

## Stack at a glance

```yaml
Framework:   Astro 6 (content-first, zero JS by default)
Islands:     Svelte components via @astrojs/svelte
Content:     Content collections with Zod schemas
Build:       Vite (built-in)
```

Reach for Astro for content sites (blogs, docs, marketing). For full-stack apps with auth/forms/interactions, use SvelteKit instead.

## Content collections

- Define schemas in `src/content/config.ts` with Zod — validated at build time.
- `type: 'content'` for Markdown/MDX, `type: 'data'` for JSON/YAML.
- Query with `getCollection('blog')`; filter with a callback.

## Islands architecture

- Components render to static HTML by default — no JS shipped.
- Add interactivity with hydration directives:
  - `client:load` — hydrate on page load.
  - `client:idle` — hydrate when the browser is idle.
  - `client:visible` — hydrate when scrolled into view.
- Use Svelte for interactive islands (`@astrojs/svelte`).

## Rendering modes

- `output: 'static'` (default) — full static site.
- `output: 'server'` — SSR for all pages.
- `output: 'hybrid'` — static by default, opt-in SSR per page.
- Per-page override: `export const prerender = true | false`.

## Project layout

```
src/content/config.ts   # collection schemas (Zod)
src/content/blog/        # Markdown/MDX content
src/pages/               # file-based routing
src/layouts/             # page layouts
src/components/          # Astro + Svelte components
```

## Testing

- If it builds, it works — content collections validate at build time.
- Unit-test utilities only if they're complex.
- E2E is usually overkill for content sites; save Playwright for apps with auth, forms, and interactions.

## See also

- [../README.md](../README.md) — TypeScript stack selection and idioms
- [sveltekit.md](sveltekit.md) — full-stack app framework
- [../../../engineering-philosophy.md](../../../engineering-philosophy.md) — universal code-health principles
