# Design Audit: God Functions and Data Clumps

You are auditing this codebase for two related anti-patterns: God Functions (functions that do too many things) and Data Clumps (groups of primitives that should be a struct/dataclass).

## What to look for

### God Functions
- Functions where you cannot describe the job without using "and"
- Functions with more than 5 parameters
- Functions with more than 3 levels of nesting in business logic
- Functions that mix I/O (file writes, network calls, DB queries) with computation

### Data Clumps
- 3+ variables that are always initialized together, passed together, or returned together
- Function signatures with >5 parameters of primitive types
- Repeated patterns of the same local variables across multiple functions

## What to do

For each finding:
1. Name the file, line, and function
2. Describe what the function does (using "and" reveals the seams)
3. Propose a specific extraction: name the new struct/function, what it contains, where it goes
4. If the project has a `baselines.json` with `file_ceilings`, note whether the refactor would reduce line count

## Scope

Default: the whole codebase. If the project's `.ai/rules/` declares hot directories (e.g., handlers, ingest pipelines, role implementations), prioritize those.

## Rules
- Do NOT change any code. Report findings only.
- Do NOT suggest changes to test files unless the test itself is a god function.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number.
- Be specific: name the variables, name the proposed struct, name the extracted function.
