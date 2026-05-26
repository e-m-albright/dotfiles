# Shared Agentic Rules

Universal guardrails for AI coding agents, independent of any specific tool.

## Process

- **Verify before claiming done.** Always run tests/builds and show output before saying something works. Evidence before assertions.
- **Brainstorm before building.** For non-trivial features, confirm requirements and approach before writing code. Ask clarifying questions.
- **Plan multi-step work.** For tasks with 3+ steps, write a brief plan and get alignment before executing.
- **Minimize surface area.** Make the smallest change that solves the request.
- **Detect stack and tooling** from existing project files before proposing commands.
- **Prefer existing project scripts/task runners** over introducing new ones.
- **If assumptions are required,** state them briefly and proceed with the safest default.

## Safety

- **Never run destructive git operations** (force push, reset --hard, branch -D) unless explicitly asked.
- **Never commit secrets or .env files.**
- **Before commits/PRs,** summarize impact and verification steps clearly.
- **Debug systematically.** When facing a bug, reproduce it first, form a hypothesis, then test that hypothesis. Don't shotgun random fixes.
- **Worktrees for isolation.** Use git worktrees for feature work when the main workspace has uncommitted changes.

## Context

- **Respect existing conventions** in the repo (formatter, linter, package manager, hook system).
- **Check the current date** before researching libraries. Search for latest docs first.

## Testing

- **TDD when testing exists.** If the project has tests, write/update tests before implementation.
- **Generate or update tests** when adding new logic, refactoring, or fixing bugs.
- **Run only what is relevant** to changed files unless asked for the full suite.
