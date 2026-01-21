# Cursor AI Rules

This file defines project-wide coding standards and rules for Cursor's AI agent.
Cursor will follow these rules when generating code, refactoring, or making suggestions.

## General Principles

- **Type Safety**: Use TypeScript strict mode. Prefer explicit types over `any`.
- **Testing**: All new features must include tests. Aim for 80%+ coverage.
- **Code Quality**: Follow ESLint and Prettier configurations. No console.log in production code.
- **Performance**: Consider bundle size and runtime performance. Avoid unnecessary re-renders.

## Code Style

- **Naming**: Use camelCase for variables and functions, PascalCase for components/classes.
- **Imports**: Organize imports: external packages → internal modules → types.
- **Components**: Prefer function components with React Hooks. Avoid class components.
- **File Extensions**: Use `.ts` for TypeScript, `.tsx` for React components.

## Next.js / React Specific

- **Server Components**: Prefer Server Components by default. Use Client Components only when needed.
- **Data Fetching**: Use Next.js App Router patterns. Fetch data in Server Components when possible.
- **Styling**: Use Tailwind CSS utility classes. Order: layout → spacing → color → typography.
- **State Management**: Use React hooks (useState, useReducer) for local state. Consider Zustand/Context for global state.

## Git & Commits

- **Commit Messages**: Use present tense verbs (e.g., "Add feature", "Fix bug", "Refactor component").
- **Branch Naming**: Use descriptive names: `feature/`, `fix/`, `refactor/` prefixes.
- **Pre-commit**: Run `npm run build` and `npm run lint` before committing.

## AI Agent Guidelines

- **Break Down Tasks**: Split large refactors into smaller, focused changes.
- **Review Generated Code**: Always review AI-generated code before committing.
- **Test Locally**: Run tests and build locally before pushing changes.
- **Context Awareness**: Reference existing patterns and conventions in the codebase.

## Security

- **Environment Variables**: Never commit `.env.local` or secrets. Use `.env.example` for documentation.
- **Dependencies**: Keep dependencies up to date. Review security advisories.
- **Input Validation**: Validate and sanitize user inputs.

## Performance

- **Bundle Size**: Monitor bundle size. Use dynamic imports for large dependencies.
- **Images**: Optimize images. Use Next.js Image component.
- **API Calls**: Implement proper caching and error handling.

---

**Note**: These rules are project-specific. Adjust as needed for your codebase.
For global Cursor settings, see `~/.cursor/cli-config.json`.
