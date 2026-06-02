# docs — the curated knowledge base

This is the repository's owned, reviewable memory: how we think about engineering, which technologies we currently favor, and the decisions behind them. An AI agent working in any project should consult this to *derive* good per-project choices — none of it is auto-pushed into projects.

- [engineering-philosophy.md](engineering-philosophy.md) — the universal principles (the lens for everything else); enforcement mechanics in [knowledge/engineering-gates.md](knowledge/engineering-gates.md)
- [stacks/](stacks/README.md) — current technology taste by language/framework (pick/avoid, idioms, patterns)
- [knowledge/](knowledge/README.md) — cross-cutting practice & tooling (AI tools, prompting, discovery, memory)
- Ephemeral agent markdown (`docs/adr/`, `docs/specs/`, `docs/plans/`, `docs/superpowers/`) — gitignored; scrub with `just scrub --artifacts`
- [developer-workflow.md](developer-workflow.md) — how this repo's tooling fits together

Setup/environment notes (machine-specific): `ides.md`, `local-llm-stack.md`, `lm-studio-local-models.md`, `agent-model-routing.md`, `pi-power-setup.md`, [`remote-shell.md`](remote-shell.md) (phone ⇄ laptop over Tailscale + Mosh + Zellij), `privacy-data-hygiene.md`, `skills-sources.md`, `tools-to-evaluate.md`.
