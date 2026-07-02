# Autonomous Research Tooling

> **Last reviewed**: 2026-07-01 — Fast-moving space; re-verify prices and product names before relying on them.

Landscape of tools for **long-horizon research, creative thinking, problem discovery, and solution engineering** — organized by *how autonomous* they are and *whether you can script them*. Companion to [ai-tools.md](ai-tools.md) (coding-assistant landscape) and [token-efficiency.md](token-efficiency.md) (model routing / cost).

**The axis that matters:** most people file these under "deep research," but they split into four tiers by autonomy. The novel, high-leverage tier — **autonomous idea generation / AI scientists** — is the one usually missed.

---

## Master table

| Tool | Vendor | Tier | Autonomous? | Scriptable API? | Cost model | Best for |
|---|---|---|---|---|---|---|
| **AI Scientist v2** | Sakana | Idea-gen | ●●● full loop | Yes (OSS) | Your model tokens | Novel hypotheses → experiment → paper |
| **AI Co-Scientist** | Google DeepMind | Idea-gen | ●●● | Limited/research | — | Biomedical hypothesis generation + critique |
| **Robin / FutureHouse Platform** | FutureHouse | Idea-gen | ●●● | **Yes** (web + API) | Per-use / API | Literature-driven scientific discovery |
| **Hermes Agent** | Nous Research | General agent | ●●● | **Yes** (self-hosted OSS) | Your infra + cheap open-weight tokens | Persistent-memory nightly research; **self-improving** |
| **Perplexity Computer** | Perplexity | General agent | ●●● async | ❌ consumer only | **Max plan $200/mo** | Async cloud tasks (hrs–weeks), 400+ integrations |
| **Claude Cowork** | Anthropic | General agent | ●●● | ❌ product | **In Claude sub** | Desktop knowledge work over local files |
| **Claude Code** (+/loop, cron) | Anthropic | General agent | ●●● | Yes (Agent SDK) | **In Claude sub** | Unsupervised engineering / PoC / discovery |
| **Manus** | Manus AI | General agent | ●●● async | Partial (api.manus.ai) | ~$20/mo credits | Unguided browse→synthesize→deliver reports in a virtual computer |
| **Kimi Researcher** | Moonshot | Deep research | ●●● | Yes (open model) | **Free / open** | RL-trained agentic research; K2.5 "Agent Swarm" up to 100 subagents |
| **OpenAI Deep Research** | OpenAI | Deep research | ●● single turn | **Yes** (`o3/o4-mini-deep-research`) | $0.40–$30/query | Breadth-first cited reports |
| **Gemini Deep Research** | Google | Deep research | ●● | **Yes** (preview) | $1–7/task or sub | Cited reports + Workspace grounding |
| **Perplexity sonar-deep-research** | Perplexity | Deep research | ●● | **Yes** | ~$0.40+/query | Cheapest DR API |
| **Claude Research** | Anthropic | Deep research | ●● | ❌ app-only | In Claude sub | Cited research inside Claude |
| **NotebookLM** | Google | Substrate | ○ you drive | Enterprise pre-GA | Bundled | Corpus grounding + audio/video overviews |
| **Open Notebook** | OSS | Substrate | ○ | **Yes** (REST) | Self-host + tokens | Self-hosted NotebookLM (18+ providers) |
| **RAGFlow / Onyx** | OSS | Substrate | ○ | **Yes** | Self-host | Retrieval engine / enterprise connectors |

Autonomy: ●●● runs a goal to a finished deliverable unsupervised · ●● one long autonomous turn · ○ a surface you operate.

---

## Tier 1 — Autonomous idea generation & scientific discovery *(the sleeper category)*

These don't just *summarize* — they **generate novel hypotheses, run experiments, and critique their own ideas**. This is the tier that matches a "wake up to new thinking" goal.

- **[Sakana AI Scientist v2](https://sakana.ai/ai-scientist-nature/)** — full cycle: idea generation → literature search → designs/codes/runs experiments via parallel agentic **tree search** → writes the paper. First AI-generated paper to pass peer review (ICLR 2025 workshop, score 6.33 > human threshold); now published in *Nature*. **Open source** — you supply the models. The reference design for autonomous discovery loops.
- **[Google DeepMind AI Co-Scientist](https://www.futurehouse.org/)** — a **multi-agent "society"** that proposes hypotheses and collaboratively critiques them (generate → debate → rank → refine). Biomedical focus. Closest published architecture to the adversarial "challenger/judge" swarm design.
- **[FutureHouse Platform](https://www.futurehouse.org/research-announcements/launching-futurehouse-platform-ai-agents)** (Eric Schmidt–backed nonprofit) — the most *usable* of this tier, **web + API**:
  - **Crow** — general scholarly Q&A, API-optimized (productionized PaperQA2).
  - **Falcon** — deep literature reviews over large DBs (OpenTargets etc.).
  - **Owl** — "has this experiment been done before?" (avoid redundant work).
  - **Phoenix** — experimental chemistry planning.
  - **[Robin](https://www.futurehouse.org/research-announcements/demonstrating-end-to-end-scientific-discovery-with-robin-a-multi-agent-system)** — multi-agent system that autonomously generated a hypothesis and **identified a novel drug candidate (ripasudil for dry AMD)**; published in *Nature*, May 2026.
  - *API pattern:* schedule Falcon/Crow to scan new publications on your thesis and summarize novel findings — a ready-made nightly-research loop.
- **[AI-Researcher (HKU)](https://openreview.net/forum?id=kQWyOYUAC4)** — autonomous scientific innovation, NeurIPS 2025 Spotlight. Plus academic systems worth mining for architecture: Agent Laboratory, MLR-Copilot, [aiXiv](https://arxiv.org/pdf/2508.15126) (open ecosystem for AI-generated papers).

**Caveat:** these are tuned for *scientific* discovery (papers, experiments). Repurposing them for general strategy/business research means keeping the loop (idea → evidence → self-critique → refine) and swapping the domain tools.

---

## Tier 2 — Autonomous general-purpose agents

Goal-to-deliverable agents that act across tools/files, not just research.

- **[Hermes Agent](https://hermes-agent.nousresearch.com/)** (Nous Research, **open source**, self-hosted) — the standout for long-horizon *owned* research. Five pillars: **persistent memory, auto-generated skills, "soul" (persona), cron scheduling, self-improvement**. Runs on your server, BYO inference (so it runs on cheap open weights). 100k★, shipping weekly since Feb 2026. See the nightly-research pitch below.
- **[Perplexity Computer](https://www.perplexity.ai/products/computer)** — ⚠️ **distinct product from Comet** (the browser). Launched Feb 25 2026, **Max plan $200/mo**. A "general-purpose digital worker": orchestrates **19 models**, runs **async in the cloud** (tasks for hours/days/weeks), run **dozens in parallel**, 400+ app integrations (Gmail, GitHub, Linear, Slack, Notion, Snowflake, Salesforce). **No public API** — consumer product, can't be a pipeline component.
- **[Claude Cowork](https://claude.com/product/cowork)** — "Claude Code power for knowledge work." Desktop agent (macOS/Windows), reads/edits/creates local files, plans+executes multi-step tasks. GA April 2026, **included for paying subscribers**. Closest zero-marginal-cost match to autonomous research for a Claude subscriber.
- **Claude Code** + `/loop` + scheduled kickoffs — the strongest *unsupervised engineering* engine, scriptable via the Agent SDK, **included in the Claude sub**.
- **[Manus](https://manus.im/)** — the canonical turnkey autonomous general agent: runs in a virtual computer, takes a fuzzy task and **browses → synthesizes → delivers a finished report/deck/app unattended**, no step-by-step prompting. Wide Research spins 100+ parallel subagents; partial API at api.manus.ai. ~$20/mo (credit-based). (Meta tried to acquire it ~$2B in Dec 2025; China's regulator blocked and unwound the deal Apr 2026 — still runs standalone.)
- **[Kimi Researcher](https://www.kimi.com/)** (Moonshot) — **free / open** autonomous deep-research agent, RL-trained for multi-step search and tool use; the K2.5 "Agent Swarm" fans out up to 100 subagents on one task. The zero-cost turnkey option, and self-hostable since the model is open-weight.
- **DeepSeek & Z.ai (the open-weight labs' own agents):** **[Z.ai](https://z.ai/)** (GLM) ships an autonomous **Agent mode** — tool-use, code interpreter, full-stack app builds — on top of GLM-5.2; a genuine turnkey agent, if not branded "deep research." **DeepSeek** has agentic web search in its chat today and V4 is built for agents, but a *dedicated* autonomous agent is reportedly slated for **end of 2026** — watch, not yet shipped. Both are the cheapest paths since the weights are open (see cost table below).
- **Genspark / Skywork / You.com ARI** — other turnkey "super agent" products in this space; capable but consumer-marketing-heavy. Evaluate directly before trusting citation-quality claims.

---

## Tier 3 — Semi-autonomous deep research (one long turn)

Read-only: excellent breadth, **no creative engineering or PoC output**. All produce cited reports.

- **[OpenAI Deep Research](https://openai.com/index/introducing-deep-research/)** — `o3-deep-research` / `o4-mini-deep-research` via Responses API. o4-mini ~10× cheaper.
- **[Gemini Deep Research](https://ai.google.dev/gemini-api/docs/deep-research)** — API (preview), async background mode, optional approved plan, Workspace grounding.
- **Perplexity `sonar-deep-research`** — cheapest DR API (~$0.40+/query).
- **Claude Research** — app-only (no API), orchestrator-worker (lead plans → parallel subagents → synthesize).

---

## Tier 4 — Not autonomous: knowledge substrates you drive

Destinations for accrued knowledge, not agents. **NotebookLM is commonly miscategorized as a research agent — it is not; it grounds and synthesizes what you feed it.**

- **NotebookLM** — corpus-grounded RAG + audio/video overviews; Enterprise API pre-GA.
- **[Open Notebook](https://github.com/lfnovo/open-notebook)** (MIT) — self-hostable NotebookLM: full REST API, 18+ providers, audio overviews.
- **RAGFlow** (best doc parsing) / **Onyx** (best connectors) — retrieval engines.

---

## Build-your-own (when nothing off-the-shelf fits at cost)

- **Framework:** [Pydantic AI](https://ai.pydantic.dev/) (typed multi-vendor agents, 4 durable-execution backends) or [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) (best checkpointing/time-travel). See [ai-coding-frameworks.md](ai-coding-frameworks.md).
- **Fork/study:** [`open_deep_research`](https://github.com/langchain-ai/open_deep_research) (cleanest multi-vendor), [GPT Researcher](https://github.com/assafelovic/gpt-researcher) (planner→crawler→publisher), [OWL/CAMEL](https://github.com/camel-ai/owl) & Co-STORM (role swarms).
- **Search layer:** Exa / Tavily / Parallel (rent web-scale search; don't rebuild it).
- The moat isn't orchestration (solved) — it's the **adversarial epistemics** (evidence tiers, N independent refuters, cross-vendor judge) and **artifact generation** (typed output schema + code sandbox for PoCs).

---

## Cost-effective models & hosting (for the build path)

Tier your models; reserve frontier spend for the judge. Prices per 1M tokens (in/out), mid-2026 — verify before relying.

| Role (volume) | Model | Price | Notes |
|---|---|---|---|
| Grunt: triage/extract | **DeepSeek V4 Flash** | $0.14 / $0.28 | Cheapest capable; 1M ctx |
| Coder / PoC | **Qwen3-Coder-Next** | $0.11 / $0.80 | No thinking blocks; tool-use tuned |
| Craft: distill | **GLM-5.2** | $1.40 / $4.40 (cache $0.26) | Beats GPT-5.5 on coding at ~1/6 cost |
| Long-horizon agentic | **Kimi K2.7 Code** | ~$0.55 / $3.20 | "Agent Swarm" up to ~300 subagents |
| **Judge / critic** | **frontier, different vendor** | premium | Where quality matters — don't cheap out |

**Where to buy:** start on **OpenRouter** (unified API, 5.5% fee, swap models per role); move hot paths to **Together/Fireworks** (own-GPU, cheapest steady per-token); **Baseten** (dedicated GPU rental) only at sustained scale or for data isolation. ⚠️ Quantization varies by host — benchmark your actual endpoint and **pin providers**. Lean on prompt caching for the shared prefix (biggest swarm lever). Cross-ref [token-efficiency.md](token-efficiency.md).

**Per-run cost reality:** frontier-only $8–30 → tiered $1.50–6 → tiered + open-weight grunt + prefix caching **$0.40–2.50**. A multi-agent turn ≈ **15× a chat turn** (Anthropic). Enforce hard per-run budget caps via a gateway (LiteLLM/Portkey) — monitoring alone won't stop a runaway.

---

## Recommendation for a Claude-heavy budget

For "best-in-class long-horizon unsupervised, don't run $10+/shot" when you already pay for Claude:

1. **Ride what's already paid** — **Cowork** (knowledge work) + **Claude Code /loop + cron** (engineering/discovery) are **$0 marginal**.
2. **Free breadth** — Gemini/ChatGPT Deep Research consumer quotas.
3. **The one place scripting pays off** — self-host **Hermes Agent** on cheap open weights for a persistent, self-improving, knowledge-accruing nightly researcher (see below). No subscription gives you this.
4. **Defer** the full custom Pydantic AI swarm until you hit a real limit of the above.
5. **Skip** Perplexity Computer unless you specifically need the async digital-worker — it's a *new* $200/mo bill on top of Claude with no API.

---

## Pitch: Hermes Agent as a nightly research engine

The goal — *schedule it to explore every night, wake up to new thinking* — is exactly what Hermes is architected for. Why it fits better than a scheduled Deep Research call:

- **It compounds.** Persistent memory (SQLite FTS + LLM summarization) + a **self-improvement loop** (every ~10 turns it decides what to save to memory or crystallize into a reusable skill) means night N+1 builds on night N. A Deep Research API call starts cold every time; Hermes accrues a knowledge base — your actual thesis.
- **Native cron.** `hermes cron start` runs the daemon; schedule with natural language or cron (`0 6 * * *`), results delivered to any connected platform (Slack, Teams, email). Zero glue code.
- **Cheap by construction.** Self-hosted, BYO inference → point it at DeepSeek V4 Flash / Qwen3-Coder-Next for the grind and a frontier model only for synthesis. Nightly runs cost cents, not the $10+/shot you're avoiding.
- **Tool gateway.** Web search, browser automation, image/TTS — enough to actually *do* research and produce artifacts, not just chat.

**Design for it (important):** cron jobs run in a **fresh session with no conversation memory** — the prompt must be self-contained. So the pattern is:

1. **Seed a "thesis" skill/memory file** — the core question, what counts as evidence, what's already known, output format. This persists across runs.
2. **Nightly cron prompt** references that file explicitly: *"Load thesis.md. Find what's new since last run, generate 3 novel angles, steel-man then attack each, append survivors to knowledge/ and write tomorrow's open questions."*
3. **Bake in the adversarial layer** — force an evidence tier per claim and a self-critique pass; that's what turns "summaries" into "new thinking that survived scrutiny."
4. **Deliver a morning digest** — top new insights + killed assumptions + next questions, to Slack/email.
5. **Let it self-improve** — over weeks it writes its own research skills (better search strategies, better critique rubrics), so the loop sharpens itself.

**Ceiling to name:** self-hosted memory is structured note-taking with retrieval (weights don't change), so quality depends on your prompts and the models you wire in — it won't out-reason a frontier model on a hard synthesis. Mitigation: route the nightly *synthesis + judge* step to a frontier model while the grind runs on open weights. Upgrade path if you outgrow it: graduate the loop into a custom Pydantic AI + DBOS swarm.

---

## Sources

- [Sakana AI Scientist (Nature)](https://sakana.ai/ai-scientist-nature/) · [AI Scientist v2 paper](https://pub.sakana.ai/ai-scientist-v2/paper/paper.pdf) · [how-to-build build secrets (Nature)](https://www.nature.com/articles/d41586-026-00899-w)
- [FutureHouse Platform](https://www.futurehouse.org/research-announcements/launching-futurehouse-platform-ai-agents) · [Robin (end-to-end discovery)](https://www.futurehouse.org/research-announcements/demonstrating-end-to-end-scientific-discovery-with-robin-a-multi-agent-system) · [AI-Researcher (OpenReview)](https://openreview.net/forum?id=kQWyOYUAC4)
- [Perplexity Computer (product)](https://www.perplexity.ai/products/computer) · [Introducing Perplexity Computer](https://www.perplexity.ai/hub/blog/introducing-perplexity-computer) · [Comet (distinct)](https://www.perplexity.ai/comet)
- [Claude Cowork](https://claude.com/product/cowork) · [Cowork GA Apr 2026](https://pasqualepillitteri.it/en/news/755/anthropic-managed-agents-cowork-ga-april-9-2026)
- [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/) · [cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) · [five pillars](https://www.mindstudio.ai/blog/hermes-agent-five-pillars-memory-skills-soul-crons) · [repo](https://github.com/NousResearch/hermes-agent)
- [OpenAI Deep Research](https://openai.com/index/introducing-deep-research/) · [Gemini Deep Research API](https://ai.google.dev/gemini-api/docs/deep-research)
- [GLM-5.2 pricing (Z.ai)](https://docs.z.ai/guides/overview/pricing) · [GLM-5.2 vs GPT-5.5 (VentureBeat)](https://venturebeat.com/technology/z-ais-open-weights-glm-5-2-beats-gpt-5-5-on-multiple-long-horizon-coding-benchmarks-for-1-6th-the-cost) · [OpenRouter models](https://openrouter.ai/models) · [Qwen3-Coder-Next](https://openrouter.ai/qwen/qwen3-coder-next/pricing)
- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
</content>
</invoke>
