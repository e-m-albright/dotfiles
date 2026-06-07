# Health Rubric

The module-health lens: grade the change against universal engineering principles, surface-specific rules, and a structural anti-pattern scan. Threads T5 (universal) and T6 (surface + structure) own this file. Grade every criterion with `file:line` evidence.

_Merged from `code-quality-audit` (rubric formerly in its SKILL.md + the anti-pattern checklist from audit-criteria.md, originally promoted from `.ai/rules/process/code-audit.mdc`)._

## T5 — Universal Criteria (all surfaces, always evaluated)

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
| **U11** | **Module Depth** | Modules pass the **deletion test**: deleting them would reintroduce complexity at multiple call sites. Small interfaces hide substantial implementation — high leverage per unit of interface a caller must learn. | Pass-through wrappers. Modules that exist only to delegate. Interface nearly as complex as the implementation. Single-adapter "seams" that just add indirection. (See `converge` skill for full vocabulary.) |

## T6 — Surface-Specific Criteria

Apply the relevant section based on detected surface(s).

### Python (when auditing `*.py`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **P1** | **Decorator Adoption** | `@timed`, `@retry`, `@cached` at boundaries. No inline `time.monotonic()`. No manual retry loops. | Ad-hoc timing, retry, caching scattered through business logic. |
| **P2** | **Import Hygiene** | `from __future__ import annotations`. `TYPE_CHECKING` blocks. Clean isort. No inline imports. | Missing annotations. Runtime type-only imports. Chaotic import order. |
| **P3** | **Type Strictness** | `pyright strict` clean. Pydantic at boundaries. No `Any` outside generic helpers. | `# type: ignore` proliferation. `dict[str, Any]` in business signatures. |

### Rust (when auditing `*.rs`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **R1** | **SQL/External Boundary Typing** | Status values use `Enum.as_ref()` in `.bind()` calls. No inline string literals in runtime queries. | Hardcoded string literals in SQL. Grep is the only safety net for renames. |
| **R2** | **Visibility Discipline** | `pub(crate)` by default. `pub` only for cross-crate API. `#[warn(unreachable_pub)]` enabled. | Everything `pub`. Accidental coupling between crates. |
| **R3** | **Error Specificity** | `thiserror` enum variants for domain errors. `anyhow` with `.context("why")` for chaining. No bare `anyhow!("failed")`. | Stringly-typed errors. Missing context. `unwrap()` in production code. |

### Web / TypeScript (when auditing `*.ts`, `*.tsx`, `*.svelte`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **W1** | **Design Token Discipline** | Tailwind classes only. Zero inline `style="font-size:..."`. Colors via CSS variables, not hex literals. | Inline styles on many elements. Hardcoded hex colors. `!important` hacks. |
| **W2** | **Single-Source Registries** | Single nav/route/command-palette source. Adding a route = 1 file edit. | Three parallel hand-maintained lists. Adding a route requires editing 4 files. |
| **W3** | **Reactive State** | State modules in dedicated files. Derived state via framework primitives (`$derived`, `useMemo`, etc.). Props down, events up. | Business logic in components. State managed via global stores and prop drilling. |

### Go (when auditing `*.go`)

| # | Criterion | What A looks like | What F looks like |
|---|-----------|-------------------|-------------------|
| **G1** | **Error Wrapping** | `fmt.Errorf("...: %w", err)` everywhere. Sentinel errors via `errors.Is/As`. | `return err` without context. String comparisons on error messages. |
| **G2** | **Context Propagation** | `ctx context.Context` is the first parameter. Always passed through. Cancellation respected. | `context.TODO()` in handlers. Goroutines started without ctx. |
| **G3** | **Interface Discipline** | Interfaces defined where consumed, not where implemented. Small interfaces. No empty `interface{}` outside generic helpers. | Large `Service` interfaces with 20 methods. Interfaces colocated with implementations. |

## T6 — Structural Anti-Pattern Scan

Drive the flexible domain observations with this checklist. Not every item applies to every change — focus on what the diff touches.

### Quick Scan

- [ ] **God Function** — >40 lines or >3 responsibilities → extract into focused functions
- [ ] **Data Clump** — same 3+ params passed together → extract into a struct/model
- [ ] **Arrow Code** — >3 levels of nesting → use early returns or extract helper
- [ ] **Lying Signature** — return type doesn't match behavior (returns null when type says non-null) → fix type or fix behavior
- [ ] **Leaky Boundary** — internal types exposed in public API → wrap in public-facing type
- [ ] **Impossible State** — type allows states that shouldn't exist → use discriminated unions/enums

### Deep Scan

- [ ] **Temporal Coupling** — must-call-A-before-B with no compile-time enforcement → combine into single operation or use typestate
- [ ] **Feature Envy** — function uses another module's data more than its own → move it to that module
- [ ] **Strategy Smell** — switch/match on type that will grow → extract strategy pattern
- [ ] **Magic Values** — unnamed constants or strings in logic → extract to named constants
- [ ] **Rule of Three** — third copy of similar code → extract shared abstraction
- [ ] **Parse Don't Validate** — validate once at boundary, use typed result downstream → push validation to edges
- [ ] **Humble Object** — complex logic near I/O boundary → extract pure logic, keep I/O wrapper thin

### Domain Check

- [ ] **Ubiquitous Language** — do code names match domain terms? Mismatched naming hides bugs.
- [ ] **Anti-Corruption Layer** — does external API vocabulary leak into domain types? Translate at the boundary.
- [ ] **Bounded Context** — does this module reach into another module's internals? Depend on its public API instead.

### AI-Generated Code Warnings

Patterns that appear frequently in LLM output — flag on sight:

- [ ] **Primitive Obsession** — bare strings/ints where enums or newtypes belong → introduce domain types
- [ ] **Logic Duplication** — same pattern across generated files (LLMs don't track prior output) → extract shared function
- [ ] **Speculative Flexibility** — abstractions for hypothetical future requirements → delete until needed
- [ ] **Leaked External Shapes** — API response field names copied into domain types → map at boundary
- [ ] **Missing Error Paths** — only happy path handled (LLMs skip edge cases) → add error handling
- [ ] **Overly Defensive** — null checks on types that can't be null → trust the type system, remove dead guards

## Flexible Criteria (domain-specific, model's judgment)

After fixed + surface criteria, identify 2–5 additional observations specific to the code being reviewed — things the rubric doesn't cover but a senior engineer would notice: architectural decisions, performance characteristics, security considerations, domain-specific correctness, clever solutions worth preserving, subtle bugs or race conditions, naming quality. Grade each as **Strength**, **Opportunity**, or **Concern**.

## Grade Calculation & Weights

| Criterion | Weight |
|-----------|--------|
| **U1 (Type Safety)**, **U3 (DRY)** | 1.5x — most impactful |
| **U11 (Module Depth)** | 1.25x — high leverage for library/framework/core domain code |
| **U10 (Concurrency Safety)** | 1.25x for async-heavy code |
| All other criteria | 1.0x |

Scale: A=4.0, A-=3.7, B+=3.3, B=3.0, B-=2.7, C+=2.3, C=2.0, C-=1.7, D=1.0, F=0.0. Overall grade = weighted average.

**Worked example** — multiply each criterion's grade-point by its weight, sum, divide by total weight, map back to a letter:

| Criterion | Grade | Points | Weight | Weighted |
|-----------|-------|--------|--------|----------|
| U1 Type Safety | B+ | 3.3 | 1.5 | 4.95 |
| U3 DRY | A- | 3.7 | 1.5 | 5.55 |
| U11 Module Depth | B | 3.0 | 1.25 | 3.75 |
| U2,U4–U10 (8 crit, avg B) | B | 3.0 | 1.0 ×8 | 24.0 |
| **Total** | | | **13.25** | **38.25** |

Overall = 38.25 / 13.25 = 2.89 → **B**. Show this table in the report so the letter is reproducible, not asserted.

## Size Thresholds by Surface

| Surface | File limit | Function limit | Justification |
|---------|-----------|----------------|---------------|
| Python | 400 lines | 50 lines | Dynamic language needs smaller units for readability |
| Rust | 800 lines | 80 lines | Type system + pattern matching allow denser code |
| Web (script) | 200 lines | 30 lines | Components should be focused; extract to dedicated state files |
| Web (markup) | No hard limit | N/A | Markup can be verbose without being complex |
| Go | 500 lines | 60 lines | Error handling adds verbosity; package-per-concern keeps files modest |

If the project has a `baselines.json` with `file_ceilings`, use those instead — projects own their thresholds.

## Calibration

- **A** — "a grumpy 15-year principal engineer would approve without comments"
- **B** — "solid, some cleanup opportunities, nothing urgent"
- **C** — "functional but accumulating debt, needs a cleanup pass"
- **D** — "significant quality issues affecting maintainability"
- **F** — "actively harmful patterns that will cause production incidents"

Post-cleanup target: **A-/B+**. Below B should not merge without addressing the top action items.
