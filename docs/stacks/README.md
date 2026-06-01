# Stacks — curated technology taste

**Taste, not mandate.** These docs capture our current opinions on languages, tools, and frameworks so an AI agent (or human) can *consult them per-project to derive appropriate choices* — not so they get pushed verbatim into every repo. The field moves fast; treat these as a strong default to argue with, not a contract.

## How to use, per project

1. Read the relevant language doc for **Selection** (pick / avoid / by phase) — most projects only need Phase 1.
2. Skim **Idioms** for how we write the language.
3. Pull **Code patterns** when you need a concrete starting point.
4. Cross-reference `../engineering-philosophy.md` (the universal principles) and any relevant `../adr/` decision.

## Languages

- [python.md](python.md) · [python-ml.md](python-ml.md) — data/ML extension
- [typescript.md](typescript.md)
- [golang.md](golang.md)
- [rust.md](rust.md)

## Frameworks

- [frameworks/fastapi.md](frameworks/fastapi.md) (Python)
- [frameworks/sveltekit.md](frameworks/sveltekit.md) · [frameworks/astro.md](frameworks/astro.md) (TS)
- [frameworks/chi.md](frameworks/chi.md) (Go)
- [frameworks/axum.md](frameworks/axum.md) · [frameworks/tauri.md](frameworks/tauri.md) (Rust)

## Cross-cutting

- [services.md](services.md) — hosting / db / auth / payments / observability picks (self-host-first)
- [infrastructure.md](infrastructure.md) — Docker, Pulumi, observability
