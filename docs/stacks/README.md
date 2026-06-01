# Stacks — curated technology taste

**Taste, not mandate.** These docs capture our current opinions on languages, tools, and frameworks so an AI agent (or human) can *consult them per-project to derive appropriate choices* — not so they get pushed verbatim into every repo. The field moves fast; treat these as a strong default to argue with, not a contract.

## How to use, per project

1. Open the language directory and read its `README.md` for **Selection** (pick / avoid / by phase) — most projects only need Phase 1.
2. Skim **Idioms** for how we write the language.
3. Pull **Code patterns** when you need a concrete starting point.
4. Check the language's `frameworks/` for the blessed framework choices.
5. Cross-reference [`../engineering-philosophy.md`](../engineering-philosophy.md) (universal principles) and any relevant [`../adr/`](../adr/) decision.

## Languages

Each language is a directory: `README.md` (selection + idioms + patterns) and a `frameworks/` subdir.

- [**python/**](python/README.md) — + [ml.md](python/ml.md) (data/ML) · frameworks: [fastapi](python/frameworks/fastapi.md)
- [**typescript/**](typescript/README.md) — frameworks: [sveltekit](typescript/frameworks/sveltekit.md), [astro](typescript/frameworks/astro.md)
- [**golang/**](golang/README.md) — frameworks: [chi](golang/frameworks/chi.md)
- [**rust/**](rust/README.md) — frameworks: [axum](rust/frameworks/axum.md), [tauri](rust/frameworks/tauri.md)

## Cross-cutting

- [services.md](services.md) — hosting / db / auth / payments / observability picks (self-host-first)
- [infrastructure.md](infrastructure.md) — Docker, Pulumi, observability
