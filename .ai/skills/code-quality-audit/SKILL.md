---
name: code-quality-audit
description: Audit code against universal engineering principles with a graded rubric. Use when reviewing modules, PRs, or conducting periodic health checks. Produces a report card with letter grades across fixed criteria plus flexible domain-specific observations.
---

# Code Quality Audit

Audit code against universal engineering principles. Produces a graded report card that communicates opportunities for improvement clearly and actionably.

## When to Use

- Reviewing a PR or feature branch before merge
- Periodic health check on a module or directory
- After a major refactor to verify quality didn't regress
- When onboarding to a module and wanting to understand its health

## Context Files

Read the philosophy first, then surface-specific rules:

1. **Universal philosophy**: `docs/engineering-philosophy.md` (project-local) or, if not present, `~/.claude/rules/process/style-principles.md` (the user-level fallback)
2. **Process rules**: any `.ai/rules/process/*.mdc` in the project
3. **Surface rules**: language-specific rules under `.ai/rules/languages/` and `.ai/rules/frameworks/`

If the project has its own `code-health-manifesto.md` or equivalent, prefer that — projects own their philosophy.

## Audit Scope

The user specifies what to audit:
- A specific file or module: `audit src/auth/middleware.rs`
- A directory: `audit web/src/lib/components/`
- A diff: `audit the changes in this PR`
- A whole surface: `audit web/`, `audit crates/`

If no scope is given, audit the unstaged changes (`git diff`).

## Detecting the Surface

Determine which language surface(s) to audit by file extension and project layout:
- `*.py` or `py/`, `python/`, `src/<package>/` with pyproject.toml → Python criteria
- `*.rs` or `crates/`, `src/` with Cargo.toml → Rust criteria
- `*.ts`, `*.tsx`, `*.svelte`, `*.vue` → Web criteria
- `*.go` or `cmd/`, `internal/` with go.mod → Go criteria
- Mixed PR → audit each surface separately, combine into one report

## Grading Rubric

### Universal Criteria (all surfaces, always evaluated)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **U1** | **Type Safety** | Every domain value has a proper type (enum, union, model). No stringly-typed business logic. Types enforced at boundaries. | Untyped dicts/strings flowing through business logic. Callers manually parse keys. |
| **U2** | **Enum Discipline** | Every string comparison uses a typed enum/union. Enums live in a canonical location. Exhaustive matching enforced. | Magic strings in comparisons across 3+ files. Typo-prone. No single source of truth. |
| **U3** | **DRY / Consolidation** | Each pattern implemented once. Lookup tables over if/elif chains. Shared abstractions in core/shared modules. No copy-paste. | Same N-line block in 3 files. Parallel if/elif chains. Per-module boilerplate. |
| **U4** | **Module Focus** | Files sized appropriately for their language. Single clear responsibility. Functions are focused. Clear seams between modules. | God modules mixing concerns. Functions doing 5 things. No clear extraction points. |
| **U5** | **Observability** | Every significant operation has a span/trace. Structured logging with context (entity IDs, operation names). No bare string warnings. | No spans. String-formatted logs. No request correlation. Invisible failures. |
| **U6** | **Test Quality** | Tests verify behavior, not implementation. Appropriate fixtures. Correct placement. No flaky patterns. | Tests mock internals. Hand-crafted fixtures duplicated. Wrong directory. |
| **U7** | **Error Handling** | Specific errors caught and logged with context. No silent swallowing. Graceful degradation where appropriate. | Silent `except: pass`. Bare catch-all. No logging on failure. User sees blank screen. |
| **U8** | **Dead Code** | No unused imports, functions, or commented-out blocks. Everything that exists is referenced. | Commented-out code. `#[allow(dead_code)]`. Unused imports. Files with zero importers. |
| **U9** | **Boundary Contracts** | External data validated at entry. Typed models for API responses, inter-service payloads, user input. Internal code trusts types. | `dict[str, Any]` flowing from API through 4 functions. String key access. Silent breakage on upstream changes. |
| **U10** | **Concurrency Safety** | Bounded fan-out (Semaphore/JoinSet/buffer_unordered). No shared mutable state without synchronization. Every query has a LIMIT. Cancel-safe async. | Unbounded gather()/join_all on external calls. Shared state mutated from multiple tasks. No limits. |

### Surface-Specific Criteria

Apply the relevant section based on detected surface(s).

#### Python (when auditing `*.py`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **P1** | **Decorator Adoption** | `@timed`, `@retry`, `@cached` at boundaries. No inline `time.monotonic()`. No manual retry loops. | Ad-hoc timing, retry, caching scattered through business logic. |
| **P2** | **Import Hygiene** | `from __future__ import annotations`. `TYPE_CHECKING` blocks. Clean isort. No inline imports. | Missing annotations. Runtime type-only imports. Chaotic import order. |
| **P3** | **Type Strictness** | `pyright strict` clean. Pydantic at boundaries. No `Any` outside generic helpers. | `# type: ignore` proliferation. `dict[str, Any]` in business signatures. |

#### Rust (when auditing `*.rs`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **R1** | **SQL/External Boundary Typing** | Status values use `Enum.as_ref()` in `.bind()` calls. No inline string literals in runtime queries. | Hardcoded string literals in SQL. Grep is the only safety net for renames. |
| **R2** | **Visibility Discipline** | `pub(crate)` by default. `pub` only for cross-crate API. `#[warn(unreachable_pub)]` enabled. | Everything `pub`. Accidental coupling between crates. |
| **R3** | **Error Specificity** | `thiserror` enum variants for domain errors. `anyhow` with `.context("why")` for chaining. No bare `anyhow!("failed")`. | Stringly-typed errors. Missing context. `unwrap()` in production code. |

#### Web / TypeScript (when auditing `*.ts`, `*.tsx`, `*.svelte`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **W1** | **Design Token Discipline** | Tailwind classes only. Zero inline `style="font-size:..."`. Colors via CSS variables, not hex literals. | Inline styles on many elements. Hardcoded hex colors. `!important` hacks. |
| **W2** | **Single-Source Registries** | Single nav/route/command-palette source. Adding a route = 1 file edit. | Three parallel hand-maintained lists. Adding a route requires editing 4 files. |
| **W3** | **Reactive State** | State modules in dedicated files. Derived state via framework primitives (`$derived`, `useMemo`, etc.). Props down, events up. | Business logic in components. State managed via global stores and prop drilling. |

#### Go (when auditing `*.go`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **G1** | **Error Wrapping** | `fmt.Errorf("...: %w", err)` everywhere. Sentinel errors via `errors.Is/As`. | `return err` without context. String comparisons on error messages. |
| **G2** | **Context Propagation** | `ctx context.Context` is the first parameter. Always passed through. Cancellation respected. | `context.TODO()` in handlers. Goroutines started without ctx. |
| **G3** | **Interface Discipline** | Interfaces defined where consumed, not where implemented. Small interfaces. No empty `interface{}` outside generic helpers. | Large `Service` interfaces with 20 methods. Interfaces colocated with implementations. |

### Flexible Criteria (domain-specific, model's judgment)

After fixed + surface criteria, identify 2–5 additional observations specific to the code being reviewed. These are things the rubric doesn't cover but a senior engineer would notice:

- Architectural decisions (good or bad)
- Performance characteristics
- Security considerations
- Domain-specific correctness
- Clever solutions worth preserving
- Subtle bugs or race conditions
- Naming quality and self-documentation

Grade each observation as: **Strength**, **Opportunity**, or **Concern**.

## Report Format

```markdown
# Code Quality Audit: [scope]

**Audited:** [files/lines examined]
**Surface:** [Python | Rust | Web | Go | Mixed]
**Overall Grade:** [A-F, weighted average]

## Report Card — Universal Criteria

| # | Criterion | Grade | Justification |
|---|-----------|-------|---------------|
| U1 | Type Safety | B+ | Most signatures typed. `flow.py:182` still uses `dict[str, Any]`. |
| U2 | Enum Discipline | A | All comparisons use StrEnum. No magic strings found. |
| ... | ... | ... | ... |

## Report Card — [Surface] Criteria

| # | Criterion | Grade | Justification |
|---|-----------|-------|---------------|
| P1 | Decorator Adoption | A- | @timed on all I/O. One manual timing in `pipeline.py:411`. |
| ... | ... | ... | ... |

## Domain Observations

### Strength: [title]
[1-3 sentences with file:line references]

### Opportunity: [title]
[1-3 sentences with file:line references and suggested fix]

### Concern: [title]
[1-3 sentences with file:line references and risk assessment]

## Top 3 Action Items

1. **[Priority]** [Specific action with file:line] — [why it matters]
2. **[Priority]** [Specific action with file:line] — [why it matters]
3. **[Priority]** [Specific action with file:line] — [why it matters]

## Grade Calculation

| Criterion | Grade | Weight | Score |
|-----------|-------|--------|-------|
| U1 Type Safety | B+ | 1.5x | 3.45 |
| U2 Enum Discipline | A | 1.0x | 4.0 |
| ... | ... | ... | ... |
| **Weighted Average** | | | **X.XX → [Letter]** |
```

## Weights

- **U1 (Type Safety)** and **U3 (DRY)**: 1.5x — most impactful
- **U10 (Concurrency Safety)**: 1.25x for async-heavy code
- All other criteria: 1.0x

Scale: A=4.0, A-=3.7, B+=3.3, B=3.0, B-=2.7, C+=2.3, C=2.0, C-=1.7, D=1.0, F=0.0

## Grading Process

1. **Detect the surface** — Python, Rust, Web, Go, or mixed
2. **Read the philosophy** — `docs/engineering-philosophy.md` (or project equivalent)
3. **Read surface-specific rules** — `.ai/rules/languages/<lang>.mdc`, `.ai/rules/frameworks/<framework>.mdc`
4. **Read the code** — every file in scope, not just samples
5. **Grep for anti-patterns** — `dict[str, Any]`, `# type: ignore`, `as any`, `unwrap()`, etc.
6. **Check structure** — file sizes (`wc -l`), function lengths, import/visibility patterns
7. **Grade each criterion** — universal + surface-specific, with file:line evidence
8. **Note domain observations** — things the rubric misses
9. **Calculate overall grade** — weighted average
10. **Prioritize action items** — top 3 most impactful improvements

## Size Thresholds by Surface

| Surface | File limit | Function limit | Justification |
|---------|-----------|----------------|---------------|
| Python | 400 lines | 50 lines | Dynamic language needs smaller units for readability |
| Rust | 800 lines | 80 lines | Type system + pattern matching allow denser code |
| Web (script) | 200 lines | 30 lines | Components should be focused; extract to dedicated state files |
| Web (markup) | No hard limit | N/A | Markup can be verbose without being complex |
| Go | 500 lines | 60 lines | Error handling adds verbosity; package-per-concern keeps files modest |

If the project has a `baselines.json` with `file_ceilings`, use those instead of the defaults — projects own their thresholds.

## Calibration

- **A overall** — "a grumpy 15-year principal engineer would approve without comments"
- **B overall** — "solid, some cleanup opportunities, nothing urgent"
- **C overall** — "functional but accumulating debt, needs a cleanup pass"
- **D overall** — "significant quality issues affecting maintainability"
- **F overall** — "actively harmful patterns that will cause production incidents"

Post-cleanup target: **A-/B+**. Below B should not merge without addressing top 3 action items.
