---
name: audit-python-contracts
description: Audit prompt for Python boundary typing — dict[str, Any] instead of models, missing edge validation, except Exception without context, type:ignore clusters, untyped public functions
stacks: python
---

# Stack Audit: Python Contracts and Boundary Typing

You are auditing this Python codebase for boundary-typing hygiene: places where a typed contract was replaced by an untyped bag, where external input enters without validation, or where failures are swallowed without context. This is a stack-specific audit — it runs only on repos that contain Python.

## What to look for

### Untyped data where a model belongs
- `dict[str, Any]` (or bare `dict`, `Dict`) flowing through function signatures and return types where the keys are known and fixed — that is a missing dataclass / Pydantic model / TypedDict
- Functions that accept a `dict` and immediately do `d["key"]` access on a known shape
- `**kwargs` passed through several layers where the real parameters are knowable

### Missing validation at the edges
- External input (HTTP body, queue message, file, env var, third-party API response) parsed by hand (`json.loads` + manual indexing) instead of validated into a model
- A Pydantic model that exists but is bypassed — input dict-accessed before it is ever constructed
- Defaults supplied at read time (`d.get("x", fallback)`) that silently absorb schema drift instead of failing loud

### Exceptions without context
- `except Exception:` (or bare `except:`) with no logging of the entity/operation context and no re-raise
- `try/except` that swallows and returns `None`/`{}`/`[]`, hiding the failure from callers
- Broad excepts around a wide block where only one narrow call can actually fail

### type: ignore clusters
- 2+ `# type: ignore` in one file or module — a cluster usually marks one untyped boundary that, once typed, dissolves all of them
- `# type: ignore` with no error code (`# type: ignore[attr-defined]`) — blanket suppression hides new errors

### Untyped public surface
- Public functions/methods with missing parameter or return annotations (especially in modules other code imports)
- Annotations that are `Any` in disguise (`object`, untyped `Callable`, `list`/`dict` without parameters) on a public boundary

## What to do

For each finding:
1. Name the file, line, and function
2. Show the untyped shape and the model/annotation that should replace it
3. Propose the fix: define the model, validate at the edge, narrow the except + add structured context, or annotate the public signature
4. For a `type: ignore` cluster, name the single underlying contract that would clear the whole cluster

## Scope

Default: the whole package. Prioritize module boundaries: request handlers, queue/worker entry points, public service interfaces, and anything parsing third-party payloads.

## Rules
- Do NOT change any code. Report findings only.
- Reference principles from `docs/engineering-philosophy.md` (or the project's equivalent) by number — especially P2 (type the domain, not the plumbing), P4 (boundaries are contracts), P7 (every exception is an event).
- Distinguish a genuinely dynamic shape (rare, justify it) from a knowable shape lazily left as a dict (the common case).
- Findings open an issue or a draft PR. Never auto-merge and never auto-apply a generative refactor.
