# Knowledge-Graph Tooling for Agents — Watch

**Status:** OPEN / discovery survey. Not an adoption decision — a tracked view of
the "queryable knowledge graph for AI agents" landscape, anchored on Graphify.

**Last surveyed:** 2026-08-04 · **Next review cue:** when a tracked tool ships a
step-change, or roughly quarterly. Star counts and pushed-dates verified via the
GitHub API on the survey date; this category moves extremely fast.

**Why this watch exists:** we already run a private SQLite-backed personal
knowledge graph (people, organizations, meetings, events) queried by agents
through a CLI. This survey asks what the code-graph and agent-memory tools are
doing that we should internalize — not whether to replace what works.

---

## The anchor: Graphify

[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — turn a
codebase plus its docs, SQL schemas, configs, and PDFs into a queryable
knowledge graph. A `/graphify` skill for Claude Code, Cursor, Codex, Gemini CLI,
and ~20 other assistants, plus a CLI and an MCP server.

**Verified traction (2026-08-04):** 102,366 stars (API-verified; marketing pages
saying "85k+" are *understated*), ~10k forks — on a repo created 2026-04-03.
Four months old, ~944 of ~1,100 commits from a single author, 804 open issues,
multiple releases per week. Apache-2.0 (with a secondary MIT file). YC S26
open-core company; the OSS skill feeds a hosted "always-on" platform waitlist.
PyPI package is `graphifyy` (name squatting), command is `graphify`.

### Architecture in brief

- **Pipeline:** `detect → extract → build_graph → cluster → analyze → report →
  export`, one module per stage, all artifacts confined to `graphify-out/`.
- **Three extraction passes:** (1) code via deterministic tree-sitter AST across
  ~36-40 grammars — zero LLM calls, fully local; (2) video/audio via local
  faster-whisper, with the transcription prompt seeded from the graph's current
  hub nodes so ASR is biased toward domain vocabulary; (3) docs/PDFs/images via
  an LLM pass — and when run as a skill, *the host agent's own subagents are the
  extraction LLM* (no API key; parallel chunk dispatch writing JSON fragments).
- **Storage:** a NetworkX node-link `graph.json` (not SQLite), plus an HTML viz,
  a markdown report, optional Neo4j/FalkorDB/GraphML/Obsidian-vault exports.
- **Schema:** nodes carry source file/location and a Leiden community id;
  rationale comments (`# WHY:`), docstrings, and ADR citations become
  first-class nodes linked to the code they explain. Edges carry a verb-phrase
  `relation`, and — the signature idea — a **confidence tag**: `EXTRACTED`
  (AST-derived, 1.0) vs `INFERRED` (LLM/resolution, discrete 0.55-0.95 rubric)
  vs `AMBIGUOUS` (flagged for human review). The tag prints in every query
  result, so an agent's citation quality is inspectable.
- **No embeddings, no vector store.** LLM-extracted `semantically_similar_to`
  edges are the similarity signal; Leiden communities do the clustering.
- **Incremental:** content-hash manifest diffing, git post-commit hook (AST-only
  rebuild, no API cost), a merge driver that union-merges the graph so parallel
  branches never conflict, and guards against silent data loss — a shrink guard
  (refuses to overwrite a larger graph with a smaller one without `--force`),
  partial-extraction refusal, dangling-edge diagnostics.

### Query surface

`graphify query "<question>"` (substring+IDF match, then BFS depth 3 or DFS
chain-tracing, **`--budget N`** caps output at ~N tokens with relevance-ranked
truncation) · `graphify path A B` (shortest path, relation + confidence per
hop) · `graphify explain X` (one node, all connections) · an MCP server with
query/node/neighbors/path/PR-impact tools · `--wiki` builds an agent-crawlable
markdown wiki per community.

Query matching is deliberately primitive (no stemming, no synonyms). The bridge
from fuzzy human phrasing to exact identifiers is a **constrained vocabulary
expansion** step: dump node-label tokens to a vocab file, let the model pick up
to 12 tokens *only from that list* — no invented synonyms, auditable, and an
empty pick means "no relevant vocabulary" rather than a hallucinated match.

### How it makes agents actually use the graph

An escalating enforcement ladder, each rung cheap and platform-tuned:

1. **Skill trigger** — the description fires on implicit codebase questions
   whenever the artifact directory exists, with a fast path that says which
   steps to *skip* ("Do not run detect. Do not ask the user to narrow.").
2. **Always-on instruction fragment** — install writes ~10 lines into
   CLAUDE.md / `.cursor/rules` / AGENTS.md that sell the *economics* ("a scoped
   subgraph, usually much smaller than raw grep output"), not just a command.
3. **PreToolUse hook** — fires before Grep/Glob/Read and nudges toward the
   graph; `--strict` blocks the first raw source read of a session (once, then
   reverts to soft nudge — it can't wedge). On platforms whose hook semantics
   reject injection (Codex), the hook is a deliberate no-op and the instruction
   file carries the load — they probed each platform's real semantics and
   encoded the differences.

### Skill authoring craft (the underrated half)

The 700-line SKILL.md is a runbook, not vibes: every step a concrete command
block with explicit success signals ("chunk file exists on disk = subagent
succeeded"), named failure modes with issue numbers inline at the exact line
where the regression bit, interpreter pinning (resolve the right Python once,
persist it, reuse it everywhere), CLI-with-inline-fallback so it degrades when
the binary is missing, and anti-misbehavior imperatives ("If you catch yourself
about to prompt for a missing API key, that is a misread of this skill").
Reference files each open with an explicit load condition ("Load this only when
the user passed `--update`"). Platform variants are *generated* from fragments
with golden-file tests — skill text treated as build output under test, not
hand-maintained prose × 20 platforms.

There's also a **work-memory loop**: `graphify save-result --outcome
useful|dead_end|corrected` records how each answer turned out; a deterministic
`reflect` pass aggregates outcomes into a LESSONS file (preferred sources,
known dead ends, corrections) that the skill reads at the *start* of the next
session, with "code changed — re-verify" staleness flags.

### Claims vs evidence

Token-compression claims are honestly caveated in their own docs (71.5x on a
52-file mixed corpus, 5.4x at 4 files, ~1x at 6 files — "six files already fits
in a context window"). BENCHMARKS.md is unusually rigorous for the genre:
shared judge model across systems, blind second-judge validation (kappa 0.81),
spend ledgers, reproduction commands, and they print the benchmark they *lose*
(supermemory beats them on raw QA at 11x ingest cost). Still self-run.

### Weaknesses

Single-JSON-blob storage (whole-file load per query, viz breaks >5k nodes);
bus factor ~1 on a 4-month-old codebase fixing self-inflicted edge cases at
weekly-release speed; semantic-pass quality is host-model dependent; the README
currently contradicts itself on query-logging defaults; open-core CTAs woven
through the docs.

---

## The landscape

### Family A — code-to-knowledge-graph for agents

| Tool | Storage | Extraction | Interface | Stars | Pushed | License |
|---|---|---|---|---|---|---|
| [Graphify](https://github.com/Graphify-Labs/graphify) | JSON/NetworkX (+Neo4j/FalkorDB export) | tree-sitter; host-agent LLM for docs | Skill + CLI + MCP | 102,366 | 08-01 | Apache-2.0 |
| [CodeGraph](https://github.com/colbymchenry/codegraph) | SQLite + FTS5 | tree-sitter, 21 langs, file-watcher sync | MCP | 64,498 | 08-01 | MIT |
| [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | SQLite (RAM-first), single static C binary | tree-sitter (158 grammars) + LSP type resolution | MCP (15 tools incl. Cypher) | 37,432 | 08-04 | MIT |
| [code-review-graph](https://github.com/tirth8205/code-review-graph) | local graph (Python) | tree-sitter + change tracking | MCP + CLI + GH Action | 28,438 | 08-02 | MIT |
| [serena](https://github.com/oraios/serena) (adjacent) | none — live LSP | language servers, no persistent graph | MCP | 27,539 | 08-04 | MIT |
| [aider repo-map](https://github.com/Aider-AI/aider) | in-process | tree-sitter + PageRank ranking | internal to CLI | 47,930 | 05-22 (stalled) | Apache-2.0 |
| [potpie](https://github.com/potpie-ai/potpie) | Neo4j | parse + LLM agents on top | own agents/API | 5,525 | 08-04 | Apache-2.0 |
| [code-graph-rag](https://github.com/vitali87/code-graph-rag) | Memgraph | tree-sitter; LLM NL→Cypher | CLI/agent | 2,511 | 08-04 | MIT |
| [pi-graphify](https://github.com/c4iov1/pi-graphify) | graphify artifacts | inherits graphify | Pi extension | 0 | 05-29 | MIT |

Notes: **CodeGraph**'s edge is always-fresh pre-indexing via OS file watchers —
the agent never queries stale structure. **codebase-memory-mcp** indexes the
Linux kernel in ~3 minutes, models Kubernetes/IaC resources as graph nodes, and
carries a preprint (arXiv:2603.27277). **code-review-graph** frames everything
diff-first: "what changed and its blast radius." **Aider's repo-map** is the
ancestor idea — a graph that exists only to select the best N tokens of
context. **serena** is the counter-bet: language servers instead of a graph.
**pi-graphify** is a thin Pi-extension wrapper; its two ideas worth noting are
proactive discovery (nudge to build a graph before one exists) and routing by
artifact fidelity (prefer the distilled wiki over raw graph JSON). Sourcegraph
has gone closed-source and is a commercial comparison point only.

The 2025→2026 convergence is unmistakable: deterministic tree-sitter →
embedded SQLite → MCP, no vector store, benchmarked in "fewer tokens / fewer
tool calls." Winners differentiate on freshness (watchers), speed (C binaries),
and query verbs (path / impact / blast-radius).

### Family B — agent-memory / KG memory layers

| Tool | What | Storage | Extraction | Stars | Distinctive idea |
|---|---|---|---|---|---|
| [Graphiti](https://github.com/getzep/graphiti) (Zep) | real-time temporal KG memory | Neo4j/FalkorDB | LLM | 29,546 | **Bi-temporal facts**: valid-time + ingestion-time on every edge; facts get *invalidated*, never deleted; point-in-time queries |
| [mem0](https://github.com/mem0ai/mem0) | universal agent memory layer | vector + KV + optional graph | LLM two-phase | 62,516 | **Reconciliation verbs**: each new fact is classified ADD / UPDATE / DELETE against existing memory, old value preserved |
| [cognee](https://github.com/topoteretes/cognee) | Extract-Cognify-Load memory pipeline | graph + vector + SQLite, pluggable | LLM | 29,772 | hybrid graph+vector, 14 retrieval modes, ontology support |
| [basic-memory](https://github.com/basicmachines-co/basic-memory) | personal KG from AI conversations | **markdown files as source of truth** + SQLite index | deterministic markdown conventions | 3,579 | human-readable files ARE the database; graph derived from note syntax, editable in Obsidian |
| [txtai](https://github.com/neuml/txtai) | embeddings DB with semantic-graph layer | SQLite + FAISS | deterministic + similarity-induced graph | 12,791 | graph induced from vector similarity — no explicit edge authoring |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | batch docs→graph→community summaries | Parquet + LanceDB | LLM + Leiden | 35,243 | community-summary hierarchy for global corpus questions; LazyGraphRAG defers summarization to query time |
| [LightRAG](https://github.com/HKUDS/LightRAG) | fast graph+vector RAG (EMNLP 2025) | embedded, pluggable | LLM, incremental | 38,504 | **dual-level retrieval**: entity-level + theme-level keys, no expensive community summarization |
| [LlamaIndex PropertyGraphIndex](https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/) | framework KG module | pluggable stores | schema-guided LLM extractors | 51,371 (repo) | declare allowed entity/relation types; the LLM fills the ontology |
| [nano-graphrag](https://github.com/gusye1234/nano-graphrag) | ~1.1k-line hackable GraphRAG | JSON/networkx | LLM | 3,956 (dormant) | minimal readable reference; spiritual parent of LightRAG |

### Family C — personal-KB surfaces for agents (brief)

[khoj](https://github.com/khoj-ai/khoj) (36.2k★, AGPL) is vector search over
notes, not an explicit graph. Obsidian MCP servers
([MarkusPfundstein](https://github.com/MarkusPfundstein/mcp-obsidian),
[cyanheads](https://github.com/cyanheads/obsidian-mcp-server)) expose files and
search, leaving the link graph implicit. **basic-memory** is the strongest
hybrid here: a local markdown vault that *is* a queryable knowledge graph over
MCP. Caveat for anyone surveying this space: the "Graphify alternatives" SEO
blogosphere is largely AI-generated listicle content with stale or invented
numbers — trust only API-verified data and primary READMEs.

---

## What we should internalize

Ideas worth adopting for a personal SQLite entity graph queried by agents,
ranked. None of these require adopting any tool above.

1. **Provenance/confidence tags on every edge** (Graphify). One column
   distinguishing evidence-backed edges (stated in a meeting, seen in a thread)
   from agent-inferred ones — printed in every view, so an agent can decide how
   much to trust an edge before acting on it.
2. **Bi-temporal facts with invalidation instead of overwrite** (Graphiti). The
   single sharpest idea in the landscape for a CRM-shaped graph: valid-from /
   valid-to / learned-at means employer changes and warmth transitions become
   queryable history ("what did I know before that meeting") rather than
   destructive updates.
3. **Token-budgeted, relevance-ranked query output** (Graphify `--budget`,
   aider repo-map). Every CLI view safe for an agent to call speculatively:
   ranked output, hard token cap, explicit "truncated — raise budget for more"
   tail instead of silent cutoff.
4. **Reconciliation verbs on ingestion** (mem0). Classify each incoming fact as
   ADD / UPDATE / INVALIDATE against existing rows, log the op, preserve the
   old value — turning an implicit reconciliation pass into an explicit,
   auditable ledger.
5. **A path/explain query surface** (Graphify, codebase-memory-mcp). "How does
   A connect to B" answered as a hop-by-hop path with provenance per hop, and
   "explain X" as one entity's full neighborhood — cheaper and sharper than
   dumping a whole CRM view.
6. **Constrained vocabulary expansion** (Graphify). Fuzzy-name resolution by
   letting the model pick only from the graph's actual label vocabulary —
   auditable, no embeddings, and an empty pick is an honest "no match."
7. **The enforcement ladder** (Graphify, pi-graphify, CodeGraph). Skill trigger
   → always-on instruction fragment that sells the economics → pre-tool nudge;
   plus self-reported index staleness so agents know when the graph can't be
   trusted.
8. **Outcome-logging work memory** (Graphify). Record which queries/views
   actually answered the question (`useful | dead_end | corrected`),
   deterministically aggregate into a lessons file read at session start, with
   staleness flags when the underlying data moved.
9. **Skill-as-tested-runbook craft** (Graphify). Explicit load conditions on
   every reference file, negative instructions as load-bearing as positive
   ones, success = artifact-on-disk, guards against silent shrink/partial
   writes, and generated-plus-golden-tested skill text.

## Open questions / to-do (tracked)

- [x] Decide which of the internalization ideas above graduate into the private
      knowledge-base CLI, and in what order. Decided 2026-08-04: #1 only for
      now — edge confidence/provenance is now printed in the notes CLI's person
      show, offered-intros, and CRM views (the schema already carried it).
      `notes path` / `--budget` and the rest were considered and parked.
- [ ] Watch whether Graphify's bus-factor/churn risk resolves (team growth,
      v1.0, storage move off single-JSON) before considering it for any real
      codebase use here.
- [ ] Re-verify star counts and activity before any adoption decision — this
      category is moving at meme-velocity and several projects are younger
      than six months.

## Sources (primary, 2026-08)

- Graphify — [repo](https://github.com/Graphify-Labs/graphify), README,
  ARCHITECTURE.md, docs/how-it-works.md, BENCHMARKS.md, `graphify/skill.md`,
  GitHub API (star/fork/license verification)
- Family A/B/C — each repo linked inline above; counts via api.github.com on
  2026-08-04
- Graphiti MCP — [help.getzep.com](https://help.getzep.com/graphiti/getting-started/mcp-server)
- LazyGraphRAG — [Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)

*Fast-moving category — re-verify before committing to anything.*
