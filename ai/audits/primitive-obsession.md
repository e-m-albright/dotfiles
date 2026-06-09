---
name: audit-primitive-obsession
description: Audit prompt for primitive obsession — raw strings/ints where a domain type belongs (IDs, money, units, status), stringly-typed enums, data clumps that are a missing value object, parse-don't-validate opportunities
stacks: python
---

# Stack Audit: Primitive Obsession and Domain Modeling

You are auditing this codebase for primitive obsession: raw `str`, `int`, `float`, and `bool` used where a domain type carries meaning, validation, and identity. The fix is to model the domain so illegal values cannot be constructed and a wrong combination of primitives cannot be passed. This is a stack-specific audit — it runs only on repos that contain Python.

## What to look for

### Raw primitives where a domain type belongs
- IDs as bare `str`/`int` — a `user_id` and an `order_id` are interchangeable to the type checker, so they get swapped silently (use a `NewType` or a small wrapper)
- Money/quantities as `float` — currency as float invites rounding bugs; this is a value object (amount + currency), not a number
- Units carried implicitly — a `timeout`, `distance`, or `size` as a bare number where the unit lives only in a comment or variable name
- Timestamps/durations as `int`/`str` instead of `datetime`/`timedelta`

### Stringly-typed enums
- A fixed set of values (status, channel, role, kind) passed and compared as raw strings (`if status == "active"`) instead of an `Enum`/`StrEnum`/`Literal`
- The same string literal compared in multiple places — a magic value that should be one named enum member
- Booleans encoding a state that actually has 3+ cases (`is_active` + `is_pending` boolean soup → a single status enum)

### Data clumps that are a missing value object
- 3+ primitives that always travel together as parameters, fields, or return tuples (e.g. `lat, lon`; `host, port, scheme`; `amount, currency`) — that group is a missing dataclass / value object
- The same cluster of locals reconstructed in several functions
- A tuple return whose elements have to be remembered by position

### Parse-don't-validate opportunities
- Code that re-checks the same precondition at every call site (`if not is_valid_email(x): ...`) instead of parsing once into an `Email` type that cannot exist invalid
- Validation that returns `bool` and leaves the caller holding the still-raw primitive, rather than returning the parsed domain value
- A model that is constructed and then re-validated downstream because the type doesn't guarantee the invariant

## What to do

For each finding:
1. Name the file, line, and the primitive(s) in question
2. Name the domain concept hiding inside the primitive
3. Propose the concrete type: a `NewType`, a frozen dataclass value object, a `StrEnum`, or a parsed wrapper — and where it should live
4. Note the bug class it prevents (swapped IDs, float money drift, invalid value reaching the core, positional-tuple mistakes)

## Scope

Default: the whole package. Prioritize the domain core and module boundaries, where a wrong primitive does the most damage.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P2 (type the domain, not the plumbing).
- Apply the Rule of Three judgment: model the concept when it recurs or carries an invariant, not on speculation for a one-off local.
- Findings open an issue or a draft PR. Never auto-merge and never auto-apply a generative refactor.
