Read and follow the instructions in AGENTS.md in this repository if present. Look for ABSTRACT.md for context on this repository.
Read all .ai/rules/*.mdc files for process and coding conventions.

## Process guardrails

- **Verify before claiming done**: Always run tests/builds and show output before saying something works. Evidence before assertions.
- **Brainstorm before building**: For non-trivial features, confirm requirements and approach before writing code. Ask clarifying questions.
- **Plan multi-step work**: For tasks with 3+ steps, write a brief plan and get alignment before executing.
- **TDD when testing exists**: If the project has tests, write/update tests before implementation.
- **Debug systematically**: When facing a bug, reproduce it first, form a hypothesis, then test that hypothesis. Don't shotgun random fixes.
- **Worktrees for isolation**: Use git worktrees for feature work when the main workspace has uncommitted changes.

## Command style

- **Prefer dedicated tools** over Bash: Read over `cat`, Glob over `find`, Grep over `grep`, Edit over `sed`.
- **Prefer single commands** over chained `&&` / `||` — chains trigger extra permission prompts.
- **Avoid `$(...)` in Bash** when a dedicated tool or simpler command works.
- **Use heredocs for commits** via the Bash tool, not echo pipelines.
