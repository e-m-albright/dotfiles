---
name: functional-core
description: The testability/effect-isolation lens of the code-health portfolio — extract a pure core and push side effects to the edges (functional core / imperative shell, ports & adapters), and model types so illegal states are unrepresentable (parse don't validate). Use when the user says "make this testable", "extract a pure core", "functional core imperative shell", "parse don't validate", "make illegal states unrepresentable", "tame the side effects", "ports and adapters / hexagonal", or "this can only be tested end-to-end". SKIP for whole-repo measured convergence (improve-codebase-architecture), bug-finding (/review), or pure deletion (subtract).
---

# Functional Core

The **effect-isolation lens**. Logic tangled with I/O can only be tested end-to-end and is hard to reason about. This lens separates the **pure core** (deterministic computation, trivially testable) from the **imperative shell** (the thin layer that does I/O), and uses the type system to make whole classes of error impossible. It's the design school behind "humble object," hexagonal architecture, and type-driven design.

It shares the dependency-categorization and seam mechanics in [../improve-codebase-architecture/references/DEEPENING.md](../improve-codebase-architecture/references/DEEPENING.md) — read it for how to test across each kind of dependency; this skill is the lens that drives toward a pure core.

## When to reach for it

A function mixes a database/network/filesystem call with the decision logic; tests need the whole stack stood up; the same data is re-validated in five places; a type can be constructed in a state the domain forbids (a "paid" order with no payment). The smell is **end-to-end-only testability** and **defensive re-checking**.

## Process

1. **Find the entanglement.** Where does computation sit inside I/O? Where is business logic only reachable by running the real adapters?
2. **Extract the pure core.** Pull the decision logic into a function that takes data in and returns data (or a description of effects) out — no I/O inside. The core becomes directly unit-testable without mocks.
3. **Leave a thin imperative shell.** The shell fetches inputs, calls the pure core, performs the effects the core described. Keep it humble — almost no logic, so little is left that only end-to-end tests can reach.
4. **Make illegal states unrepresentable.** Model the types so the forbidden state can't be constructed: enums/unions over boolean soup, a `PaidOrder` type that *can't* exist without a payment, `Option`/`Result` over null-and-throw. **Parse, don't validate** — turn unstructured input into a precise type once, at the boundary, then trust it inside.
5. **Define errors out of existence** where you can (Ousterhout): redesign semantics so the error case doesn't arise, rather than making every caller handle it.
6. **Test the core directly; test the shell with one or two integration tests.** The interface is the test surface.

## Antagonists

- **vs `subtract`/YAGNI:** introducing ports, adapter seams, and richer types adds structure. Tiebreak: **only isolate effects where entanglement actually blocks testing or reasoning** — don't add a port for a single in-process call (one adapter is a hypothetical seam; two is a real one).
- **vs `tidy`:** extracting a pure core is a bigger move than a mechanical transform; sequence the mechanical tidies first to make the extraction obvious.
- **vs `deepen`:** strongly aligned — a pure core *is* a deep module. Use `deepen`'s vocabulary for the interface.

## Sources
- Bernhardt, *Functional Core, Imperative Shell*; Cockburn, *Hexagonal Architecture* (ports & adapters); Wlaschin, *Parse, Don't Validate* / *Domain Modeling Made Functional* (make illegal states unrepresentable); Ousterhout, *define errors out of existence*; "humble object" (Feathers). Dependency/seam testing detail in [DEEPENING.md](../improve-codebase-architecture/references/DEEPENING.md).
