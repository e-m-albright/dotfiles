# Universal Style Principles

These principles apply across all languages and frameworks.

## Code Organization

### File Structure
- **One concept per file** — A file should do one thing well
- **Flat over nested** — Prefer `components/Button.tsx` over `components/buttons/primary/Button.tsx`
- **Colocate related code** — Tests next to source, styles next to components
- **Index files are for re-exports only** — No logic in `index.ts`

### Naming
- **Descriptive over clever** — `getUserById` not `fetchUsr`
- **Consistent casing** — Follow language conventions (camelCase JS, snake_case Python, etc.)
- **No abbreviations** — `configuration` not `cfg`, `response` not `res`
- **Boolean prefix** — `isActive`, `hasPermission`, `canEdit`

### Functions
- **Single responsibility** — One function, one job
- **Pure when possible** — Same input = same output, no side effects
- **Early returns** — Reduce nesting with guard clauses
- **Max 3 parameters** — Use objects for more

## Comments & Documentation

### When to Comment
- **Why, not what** — Code shows what; comments explain why
- **Complex algorithms** — Brief explanation of the approach
- **Workarounds** — Link to issue/PR explaining the hack
- **Public APIs** — Document inputs, outputs, side effects

### When NOT to Comment
- **Obvious code** — `i++ // increment i` is noise
- **Commented-out code** — Delete it; git remembers
- **TODOs without tickets** — Create an issue instead

## Error Handling

### Principles
- **Fail fast** — Validate inputs at boundaries
- **Be specific** — `UserNotFoundError` not `Error("something went wrong")`
- **Log context** — Include relevant IDs, timestamps, request info
- **User-friendly messages** — Technical details in logs, helpful text for users

### Anti-patterns
- **Silent failures** — Never swallow exceptions
- **Generic catches** — Don't `catch (e) {}` without handling
- **Error strings** — Use typed errors, not string matching

## Testing Philosophy

### Test Pyramid
1. **Unit tests** (many) — Fast, isolated, test logic
2. **Integration tests** (some) — Test boundaries, APIs, database
3. **E2E tests** (few) — Critical user paths only

### What to Test
- **Behavior, not implementation** — Test what it does, not how
- **Edge cases** — Empty arrays, null values, boundaries
- **Error paths** — Ensure failures are handled correctly
- **Public APIs** — Internal helpers can change

### What NOT to Test
- **Framework code** — Don't test that React renders
- **Trivial code** — Getters, simple mappings
- **External services** — Mock them, don't call them

## Performance Mindset

### Think First
- **Measure before optimizing** — Profile, don't guess
- **Optimize hot paths** — 80/20 rule applies
- **Consider N+1** — Database queries, API calls, renders

### Defaults
- **Lazy load** — Load code/data when needed
- **Paginate** — Never return unbounded lists
- **Cache wisely** — Invalidation is hard; be explicit

## Security Defaults

### Always
- **Validate all inputs** — Trust nothing from users
- **Parameterize queries** — Never concatenate SQL
- **Escape output** — Context-appropriate encoding
- **HTTPS everywhere** — No exceptions in production

### Never
- **Secrets in code** — Use environment variables
- **Sensitive data in URLs** — Query params are logged
- **Overly permissive CORS** — Whitelist origins
