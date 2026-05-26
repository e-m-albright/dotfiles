# Tools to Evaluate

Bookmarked tools and services worth investigating.

## Security / Static Analysis

- **[Semgrep](https://semgrep.dev)** -- Pattern-based SAST/SCA/secrets platform unifying static analysis with AI reasoning to detect IDORs, broken authz, and other logic-level vulnerabilities. Lightweight grep-like custom rule syntax plus reachability analysis (vendor claims 98% false-positive reduction). OSS Community Edition (free, self-hostable) plus SaaS AppSec Platform. Evaluate when you want fast SAST/secrets coverage with custom rules in CI without standing up a heavy platform.
- **[SonarQube](https://www.sonarsource.com/products/sonarqube/)** -- Code quality and security analysis covering 40+ languages with bug/vulnerability/code-smell detection. Quality Gates enforce deployment standards; SonarLint feeds the same rules into the IDE. Community Build OSS; Team plan ~$32/mo; Enterprise custom. Evaluate when you want enterprise-grade quality gates and broad language coverage across IDE + CI, especially for AI-generated code review.

## CI / CD

- **Blacksmith vs Depot** -- both are drop-in replacements for GitHub Actions runners with ~2-10x speed/cost claims. **Blacksmith** ([blacksmith.sh](https://blacksmith.sh)) leans bare-metal gaming-CPU hardware + Docker layer cache on NVMe; 60-75% cost reduction vs GHA; 3,000 free minutes/month. **Depot** ([depot.dev](https://depot.dev)) has a wider product surface (remote BuildKit, distributed cache, programmable CI engine, Build API) and per-second billing; claims 10x faster workflows / 40x faster Docker builds. **Recommendation**: try Depot first (broader surface, mature cache story); benchmark Blacksmith for raw runner speed on Docker-heavy pipelines.
- **[Depot](https://depot.dev)** -- Remote Docker builder + GHA runners + distributed remote cache + programmable CI engine. Claims ~30% faster CPUs and 10x networking on runners; per-second billing; unrestricted concurrency. Evaluate when Docker builds or GHA runtime are the bottleneck.
- **GitHub Actions paid runners** ([github.com/features/actions](https://github.com/features/actions)) -- Baseline. Free on public repos; private repos billed per-minute by runner class. macOS and large runners are the cost driver that motivates Depot/Blacksmith/Namespace.
- **[CircleCI](https://circleci.com)** -- Mature CI/CD now branding as "autonomous validation" with test intelligence and rollback pipelines. Chunk Agent claims 97% faster test runs; MCP server for AI-driven failure diagnosis. Freemium credit-based pricing; cloud/hybrid/on-prem. Startup program offers up to $20k credits. Evaluate for large team / complex matrix needing strong test parallelization.
- **[Semaphore](https://semaphoreci.com)** -- Cloud CI/CD positioned explicitly on speed -- vendor benchmarks claim 94% faster than GHA at ~$0.04/job vs GHA's ~$0.06. OSS Community Edition (self-hostable) plus pay-as-you-go cloud. Evaluate for performance-sensitive pipelines where managed beats self-hosted.
- **[Buildkite](https://buildkite.com)** -- Hybrid model: SaaS control plane, BYO agents. **Yes, you can use a local machine as a runner** -- that's the core model. Agents run anywhere (laptop, server, K8s, GPU, on-prem). Per-user pricing on self-hosted agents (not per-minute). Hosted Mac/Linux agents are an add-on. Evaluate when you need SaaS orchestration over specific hardware (GPUs, secured networks, your own laptop).

### Build Infra

- **[Docker BuildKit](https://github.com/moby/buildkit)** -- Modern Moby builder backend; concurrent, cache-efficient, Dockerfile-agnostic. Default since Docker Engine 23.0. Powers Depot, Blacksmith, Namespace under the hood. Worth understanding directly when tuning cache strategy or going rootless.
- **[Docker buildx](https://docs.docker.com/build/buildkit/)** -- Docker CLI plugin exposing BuildKit features; the `docker buildx` command. First-class multi-arch builds (`linux/amd64` + `linux/arm64` in one command) and remote builder connections. Bundled with Docker Desktop.
- **[Namespace](https://namespace.so)** -- Developer infra: fast GHA/GitLab runner replacements + isolated cloud Devboxes + remote caching for Docker/Bazel/Turbo/Nix. Sub-second (~900ms) instance boot. Broader cache coverage than Depot (Bazel/Turbo/Nix in addition to Docker) plus Devboxes for AI coding agents. Evaluate if you want CI acceleration plus on-demand cloud workspaces for agents.

## Git Hosting

- **[Codeberg](https://codeberg.org)** -- Non-profit git hosting (Codeberg e.V., Berlin) on the OSS Forgejo platform. Community-governed, EU-hosted, no tracking/ads/data sale. Built-in CI and Pages. Free (donations / membership). Evaluate for hosting OSS outside big tech or for EU data residency with a non-commercial ethos.
- **[GitLab](https://about.gitlab.com)** -- Single-platform DevSecOps: git + CI/CD + planning + integrated SAST/SCA/secrets/DAST + AI agents (GitLab Duo). OSS Community Edition (self-hosted) plus SaaS at gitlab.com. Premium/Ultimate paid tiers; Ultimate adds the security suite. Evaluate when you want a one-vendor full stack with strong self-hosted story or built-in security/compliance reporting.
- **[Sourcehut](https://sr.ht)** -- Minimalist OSS forge by Drew DeVault: git/Mercurial, mailing lists, issue tracking, CI, wikis, chat -- email-driven workflows. No JavaScript required, no tracking, no AI features; patches via `git send-email`. Paid subscription supports the project; still public alpha. Evaluate for maximum data portability and terminal/email-native workflow.

## Code Review

- **[CodeRabbit](https://coderabbit.ai)** -- AI PR review with 40+ linter/security-scanner integrations plus IDE + CLI review modes. Codegraph-based codebase understanding; learns from natural-language feedback. SaaS per-seat; SOC 2 Type II, zero data retention. 15k+ customers. Evaluate for broad-coverage AI review with high configurability via YAML.
- **[Greptile](https://www.greptile.com)** -- (User likely meant this; "Reptile" is not a code-review tool.) AI code-review agent that builds a graph index of the codebase and runs parallel agents to review PRs with full repo context. Benchmarks claim it flags more critical bugs than major competitors. Used by Stripe, Amazon. **Confirm: is Greptile what you meant by "Reptile"?**
- **[Graphite](https://graphite.com)** -- Code-review platform built around **stacked PRs** (no other vendor really competes here) plus Diamond AI review and a stack-aware merge queue. CLI + VS Code extension. Per-seat paid tiers. Evaluate if the team hits review bottlenecks on large PRs and you want to adopt stacked-diff workflow.
- **[Cursor BugBot](https://cursor.com/bugbot)** -- Cursor's AI PR-review bot, tuned for high signal-to-noise on logic bugs (not style); vendor claims >50% of flags get fixed pre-merge; strong on AI-generated code. Customizable via BugBot Rules. Evaluate if already in Cursor's ecosystem.
- **[Claude Code Review (GitHub Action)](https://github.com/anthropics/claude-code-action)** -- Anthropic's official Action that runs Claude Code on PRs to post inline comments on logic, security, edge cases, regressions. Same engine as local Claude Code; fleet of specialized agents; `/security-review` slash command; severity-tagged but non-blocking. Install via `/install-github-app` from Claude Code. **Announcement**: [claude.com/blog/code-review](https://claude.com/blog/code-review) -- internally raised substantive PR comments from 16% to 54%. Pay Anthropic API + CI minutes.
- **[Macroscope](https://macroscope.com)** -- AI code review + engineering-intelligence platform (PR bug detection, commit/status summaries, Slack/GitHub agent for engineering Q&A). AST-based graph analysis (not embeddings); learns from accepted vs rejected comments; explicitly does not train on user code. Usage-based pricing ($0.05/KB review, $0.05/commit status). **Caveat**: user-reported "exact strength for Python/TypeScript/Go" is **not corroborated by the homepage** -- no published language list. Confirm via demo before evaluating on that basis.

> **Strategic consideration**: an alternative to picking one is a **homegrown AI review scaffold** -- Claude Code Action + strict static checkers (Ruff, mypy, ESLint, golangci-lint, Semgrep) that emit graded reports and block CI. Custom rubric, no per-seat lock-in, lives in your repo. Worth a spike before committing to a SaaS code-review vendor for 12+ months.

### Additional AI code review entries

- **[Qodo](https://qodo.ai)** (formerly CodiumAI) -- Enterprise pick for large monorepos. Built on the OSS [PR-Agent](https://github.com/qodo-ai/pr-agent). monday.com prevents 800+ issues/month at 73.8% suggestion-acceptance. Configurable rule system, indexes many repos. PR-Agent is self-hostable for air-gapped/private deploys.
- **[GitHub Copilot Code Review](https://github.blog/changelog/copilot-code-review/)** -- Native, zero-setup, included with Copilot subscription. GA April 2025, 1M users in first month. The "if you already pay for Copilot, turn it on" option.
- **[CodeAnt AI](https://www.codeant.ai/)** -- Line-by-line review + security scanning + DORA tracking. 30+ languages.
- **[Panto AI](https://panto.ai/)** -- DevSecOps flavor: secrets + dependency + IaC + code review in one workflow. Compliance-heavy environments.
- **[Sourcegraph Cody](https://sourcegraph.com/cody)** -- Code-aware Q&A and review hints across very large codebases. Pair with, not replace, dedicated PR reviewers.
- **[Augment Code](https://www.augmentcode.com/)** -- VC-darling for enterprise monorepos; indexes hundreds of services. Evaluate for very large polyglot codebases.
- **[Codacy](https://www.codacy.com/)** -- Predominantly rule-based with AI layered on. Multi-language quality gates.
- **[Snyk Code](https://snyk.io/product/snyk-code/) / [Semgrep](https://semgrep.dev)** -- Security-specialized scanners (Semgrep already tracked under Security/Static Analysis). Run alongside, not instead of, an AI reviewer.
- **[Qodana (JetBrains)](https://www.jetbrains.com/qodana/)** -- IDE/CI parity for JetBrains shops.
- **[GitLab Duo](https://about.gitlab.com/gitlab-duo/)** -- GitLab-native review. Solid if you're on GitLab.
- **Devlo / Atlassian Rovo** -- Newer entrants inside Bitbucket/Jira ecosystems.

## Web / Frontend

- **[Zero (Rocicorp)](https://zero.rocicorp.dev/)** -- General-purpose sync engine for local-first apps. Instant local reads + server reconciliation; optimistic mutations with built-in conflict resolution. Pitch: "absurdly fast" UI because data is already on-device. Worth evaluating for any product where perceived latency dominates (especially LLM-backed UIs where the model call is slow). See Scott Tolinski's video ([YouTube](https://www.youtube.com/watch?v=aV6aM3R74AQ)) for the practitioner take.
- **[Storybook](https://storybook.js.org/)** -- Component workshop / dev environment for UI components in isolation. The de facto standard for design-system documentation, visual regression testing, and component-level interaction testing. Evaluate when component count crosses ~30 and review-by-screenshot becomes a bottleneck. Pairs naturally with Chromatic for visual diffing.
- **[Framer Motion](https://www.framer.com/motion/)** -- React animation library with a declarative API (`motion.div` + `animate` / `initial` / `exit` props). The mainstream choice for "we need animations beyond CSS transitions but don't want to wire up GSAP." Strong gesture support (drag, pan, hover) and layout animations. Evaluate for any UI where motion telegraphs state changes (loading, success, list reorder).
- **[Base UI](https://base-ui.com/)** -- Unstyled, accessible React component primitives from the team behind Radix UI and Material UI. Headless: you bring the styles. Successor / sibling to Radix Primitives. Evaluate when building a custom design system and want correctness (a11y, keyboard, focus management) without inheriting visual opinion. Likely default over Radix for new projects in 2026.
- **[TanStack](https://tanstack.com)** -- Type-safe data fetching, routing, forms. Evaluate for replacing ad-hoc React data layer.
- **[Vite+](https://voidzero.dev/posts/announcing-vite-plus)** -- Next-gen build tool from VoidZero. Watch for stability and ecosystem uptake.
- **[Leptos](https://leptos.dev)** -- Rust full-stack web framework. Evaluate for Rust-heavy teams.
- **[Dioxus](https://dioxuslabs.com/)** -- Rust full-stack crossplatform app framework (web, desktop, mobile). Alternative to Leptos; evaluate when a single Rust codebase needs to ship to multiple platforms.
- **Enhance** -- Backend-first web framework. Read: [How To Build an App With Enhance](https://thenewstack.io/how-to-build-an-app-with-enhance-a-backend-first-framework/).

## CMS / Content

- **[EmDash CMS (Cloudflare)](https://www.producthunt.com/products/emdash-cms)** -- TypeScript CMS positioned as WordPress alternative. On our platform already.
- **[Payload CMS on Cloudflare Workers](https://blog.cloudflare.com/payload-cms-workers/)** -- Full-fledged CMS running entirely on Cloudflare's stack.
- **[MarkdownCMS](https://markdowncms.netlify.app/)** + **[waynesutton/markdown-site](https://github.com/waynesutton/markdown-site)** -- Lightweight markdown-driven sites.

## CLI Libraries

- **[Ink](https://github.com/vadimdemedes/ink)** -- React renderer for terminal UIs by Vadim Demedes; uses Yoga flexbox so you write CLIs with the same component model as the web. **Battle-tested**: powers Claude Code, GitHub Copilot CLI, Gemini CLI, Wrangler, Shopify CLI, Prisma. OSS (MIT), 38.4k stars. Evaluate for any non-trivial Node/TS CLI with interactive UI. Maintainer policy: fully AI-generated PRs are rejected.

## Terminal Stack

> Currently installed via `brew.sh`: ghostty, helix, yazi, ripgrep, fd, fzf, zoxide. Pending evaluation below.

- **[Warp](https://www.warp.dev/)** -- Terminal explicitly designed for **multi-agent dev**. Supports Codex, OpenCode, Gemini CLI as first-class threads with vertical tabs, configurable per-agent metadata (branch, worktree, PR), unified notification center. Send inline comments/snippets/files directly to a running agent session. Evaluate when juggling multiple Claude Code instances across worktrees becomes painful in plain Ghostty.
- **[Yazelix](https://github.com/luccahuguet/yazelix)** -- Reproducible terminal IDE bundling **Yazi + Zellij + Helix** with an AI-aware layout. Would require installing Zellij. Aspirational target for fully-terminal IDE workflow.
- **[Zellij](https://zellij.dev/)** -- Modern tmux alternative. Discoverable keybindings, YAML/KDL layouts, plugin system. Prerequisite for Yazelix.
- **[Atuin](https://atuin.sh/)** -- Command history in SQLite with full-screen fuzzy search on the up-arrow + cross-machine sync. Evaluate as a `Ctrl-R` upgrade.
- **[Lazygit](https://github.com/jesseduffield/lazygit)** -- TUI for git, faster than CLI for hunk staging, rebasing, diffs. **Especially valuable alongside AI agents** -- file-level diff view gives precise control over every AI-touched line before committing.
- **[Lazydocker](https://github.com/jesseduffield/lazydocker)** -- Same TUI pattern for containers.
- **[Btop](https://github.com/aristocratos/btop)** -- Prettier, faster htop replacement.
- **[eza](https://eza.rocks/)** -- `ls` with git status, icons, tree mode. Successor to `exa`.
- **[bat](https://github.com/sharkdp/bat)** -- `cat` with syntax highlighting + git markers; doubles as a pager for other tools (`--pager`).
- **[delta](https://github.com/dandavison/delta)** -- Git's diff viewer rewritten: side-by-side, syntax highlighting, proper word-level highlights.
- **[difftastic](https://difftastic.wilfred.me.uk/)** -- **Structural (AST-based) diffs** that ignore reformatting noise. Devastating once you try it on a refactor PR.
- **[Starship](https://starship.rs/)** -- Fast cross-shell prompt surfacing git, k8s context, exec time, language versions. Cross-platform.
- **[sesh](https://github.com/joshmedeski/sesh)** -- Session picker fusing tmux + zoxide + fzf. One-keystroke project jump from anywhere.
- **[fish](https://fishshell.com/)** -- Shell with sane defaults + autosuggestions without a plugin manager. Alternative to zsh+plugins.

## Editors / Terminals

- **[Zed editor](https://zed.dev)** -- Modern editor written in Rust, GPU-accelerated rendering. Open-sourced Jan 2024. Positions as a native-performance alternative to Cursor/VS Code -- the tradeoff is a smaller extension ecosystem (no VS Code Marketplace). Built-in real-time collaborative editing ("channels") and an agentic AI edit mode. Worth a side-by-side with Cursor specifically for Python work given recent LSP investment; less compelling if our Cursor extension setup is load-bearing. Python, Markdown, LSP-first. Reading: [Making Python in Zed Fun](https://zed.dev/blog/making-python-in-zed-fun), [Settings UI rebuild](https://zed.dev/blog/settings-ui).
- **[Ghostty 1.3.0](https://www.xda-developers.com/ghostty-13-terminal-makes-finding-your-previous-commands-a-ton-easier/)** -- Modern terminal. Improved previous-command search.

## Runtimes / Languages

- **[Bun v3.1](https://www.infoq.com/news/2026/01/bun-v3-1-release/)** -- JS runtime / bundler. Evaluate for build-step consolidation.
- **[Pyodide](https://thenewstack.io/run-real-python-in-browsers-with-pyodide-and-webassembly/)** -- Real Python in the browser via WebAssembly.
- **[Python 3.14 Lazy Annotations](https://realpython.com/python-annotations/)** -- New deferred-evaluation annotations behavior. Check impact on our typing patterns.
- **[Zig](https://ziglang.org)** -- Systems language positioned between Rust (safety-first, borrow checker) and C (minimal, unsafe): no hidden control flow, no hidden allocations, explicit memory management without a borrow checker. Excellent cross-compilation -- `zig cc` works as a drop-in C cross-compiler even if you never write Zig (Bun uses it this way for its native parts). Smaller ecosystem than Rust; language still pre-1.0 and evolving. Worth exploring for performance-critical tooling where Rust's safety discipline feels like overhead, or as a gentler C-replacement for embedded/systems work.
- **[uvloop](https://github.com/MagicStack/uvloop)** -- Drop-in replacement for the default Python `asyncio` event loop, built on libuv. Roughly 2-4x faster on typical async workloads; one-line install (`import uvloop; uvloop.install()`). The right default for any Python service that's I/O-bound (HTTP clients, WebSocket servers, LLM call fanout). Already a transitive dep of uv/uvicorn-fast-path. See also [[Knowledge/Software-Engineering/Architecture-Patterns]] for why this fits the 12-factor "stateless processes" tier.
- **[Granian](https://github.com/emmett-framework/granian)** -- Rust-based PSGI/ASGI/WSGI HTTP server for Python. Alternative to uvicorn/gunicorn with lower overhead and built-in support for HTTP/1, HTTP/2, and WebSockets. Evaluate as the production runner for FastAPI services where uvicorn's overhead becomes measurable (see the FastAPI vs Fiber benchmark -- Granian narrows the gap with Go). Drop-in for most ASGI apps.

## Data

- **[DuckDB WebAssembly](https://www.infoq.com/news/2026/01/duckdb-iceberg-browser-s3/)** -- Query Iceberg datasets in the browser.
- **[Turso](https://thenewstack.io/why-we-created-turso-a-rust-based-rewrite-of-sqlite/)** -- Rust rewrite of SQLite. Edge-native.
- **[MotherDuck semantic layer for DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)** -- Semantic layer tutorial.
- **[Pandera](https://github.com/unionai-oss/pandera)** -- Declarative schema validation for dataframes (pandas, Polars, PySpark, Modin, Dask). Pydantic-style `DataFrameModel` class API plus statistical hypothesis checks. The right default for validating ETL boundaries and the contract between untrusted input and downstream analytics. Catches schema drift at the boundary instead of through defensive code in pipeline logic.
- **[Polars Cloud](https://cloud.pola.rs/)** -- Managed serverless Polars compute. Same Polars API runs on a laptop or scales across distributed clusters; pay-per-second, no idle charges. AWS now, GCP/Azure planned. Worth tracking when a pandas/Polars pipeline outgrows a single machine but a full Spark cluster is overkill.

## Infra / DevOps

- **[OpenTelemetry "Demystifying OpenTelemetry" guide](https://www.infoq.com/news/2026/02/opentelemetry-observability/)** -- New OTel intro guide worth skimming before our next observability rollout.

## Kubernetes / GitOps

> Not currently using Kubernetes. Evaluate as a group when a project outgrows Fly/Railway/Cloudflare Workers or needs multi-region orchestration beyond what PaaS offers. These tools travel together -- adopt as a set if at all.

- **ArgoCD** -- GitOps continuous delivery for Kubernetes. Declarative, git-driven deployments reconciled from a repo. Evaluate against **Flux** (lighter, CNCF-graduated) and **Rancher Fleet** (multi-cluster focus).
- **Helm** -- De facto package manager for Kubernetes ("apt for k8s"). Charts templatize manifests. Widely used but criticized for Go-template complexity; watch **Kustomize** (overlays, no templating) and **Kluctl** as alternatives depending on preference for templating vs. patching.
- **[Fly Kubernetes](https://fly.io/docs/kubernetes/)** -- Managed k8s on Fly's edge network. Lower ops burden than EKS/GKE. Compelling if we outgrow Fly Machines but want to stay on Fly.
- **kubectl / k9s** -- Canonical CLIs. `kubectl` is the control-plane client; `k9s` is a TUI dashboard. Install via Homebrew when k8s becomes real -- not before.
- **Consider also**: **Tilt** / **Skaffold** (inner dev loop), **cert-manager** (TLS automation), **external-secrets** (pulls secrets from Vault/AWS/etc. into k8s).

## AI / Dev Workflow

- **[OpenSpec](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md)** -- Spec-driven dev workflow (Fission-AI). See also: [[Knowledge/Software-Engineering/Spec-Driven-Development]].
- **[Open-WebUI Open Terminal](https://github.com/open-webui/open-terminal?ref=console.dev)** -- Terminal from the Open-WebUI project.
- **[Microsoft FARA](https://github.com/microsoft/fara)** -- Microsoft agentic framework. Check positioning vs. Semantic Kernel / AutoGen.
- **[Browserbase](https://www.browserbase.com/)** -- Managed headless-browser infrastructure built for AI agents. Run Playwright/Puppeteer at scale without provisioning Chromium yourself; includes session recording, stealth/anti-bot handling, and proxy management. Evaluate for any agent workflow that needs to drive a real browser (form filling, scraping, web-based tool use). Likely cheaper and more reliable than rolling our own browser pool.
- **[Sandcastle](https://github.com/mattpocock/sandcastle)** -- TypeScript library for orchestrating "AFK" (away-from-keyboard) coding agents in isolated sandboxes. Workflow: front-load context via a grilling session with the human, then delegate execution to a sandboxed environment where the agent runs tests and fixes bugs autonomously. Pairs with vertical-slice TDD and markdown Kanban boards as agent state. Worth evaluating once we have a workflow that hits the "I trust this agent to run for an hour unattended" bar. See [Matt Pocock's video](https://www.youtube.com/watch?v=E5-QK3CDVQM).
- **[OpenWhispr](https://openwhispr.com/)** -- Free, open-source system-wide dictation for macOS using local Whisper models. GPU-accelerated, custom dictionaries, filler-word removal, fully offline. Privacy-focused alternative to subscription tools (WhisperFlow, MacWhisper). Evaluate when current dictation workflow gets painful or when sending audio to the cloud becomes a compliance problem.
- **[Magic Patterns](https://magicpatterns.com/)** -- AI tool for generating UI/UX patterns from text prompts. Pitched as "describe a UI, get production-ready React/Tailwind code." Mentioned in Garry Tan's "20x Company" video as part of the toolchain that lets tiny teams ship product surface area without dedicated design hires. Evaluate when prototyping needs to skip the Figma round-trip; reality-check the code quality before committing.
- **[LLMLingua](https://github.com/microsoft/LLMLingua)** -- Microsoft's LLM-based prompt-compression library. Compresses long contexts by an order of magnitude while preserving most task accuracy, via a small model that scores token importance. Pairs with [[Knowledge/LLMs-and-AI/Context-Engineering]]: high-leverage when prompts are bumping the cost/latency budget and reranking alone isn't enough.
- **[Vercel AI SDK](https://ai-sdk.dev)** -- TypeScript framework providing a unified interface across 100+ LLMs / 16+ providers for text, image, speech, video, tools, and structured output. Provider-agnostic (swap OpenAI/Anthropic/Google with a one-line change); first-class streaming primitives for React/Next/Vue/Svelte/Node. OSS (Apache 2.0), 13M weekly downloads, 24.2k stars. Default for any TS-based product needing LLM calls with streaming without provider lock-in. Cookbook example -- [Natural Language Postgres](https://ai-sdk.dev/cookbook/guides/natural-language-postgres) (NL-to-SQL with GPT-4o + Zod + auto-charting).
- **[spec-kit](https://github.com/github/spec-kit)** -- GitHub's OSS toolkit for spec-driven development. Slash commands (`/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`) walk an AI agent from intent through implementation. Works across 30+ agents (Copilot, Claude, Gemini, etc.). **Compare against** `superpowers:writing-plans` before adopting -- significant overlap; pick one discipline.
- **[Jules (Google)](https://jules.google)** -- Async coding agent (Gemini-powered) that clones your repo into a Google Cloud VM and works in the background, returning a PR. Fire-and-forget execution model; concurrent task support; "Jules Tools" CLI for scripting. Three tiers: free, Google AI Pro, Google AI Ultra (multi-agent). Evaluate as an alternative to Codex Cloud / Claude Code background tasks for backlog churn (deps bumps, test writing, small features).
- **[Claude in Chrome (beta)](https://code.claude.com/docs/en/chrome)** -- Anthropic's official Chrome extension + `claude --chrome` / `/chrome` slash command for browser automation: live debugging, design verification, form filling, data extraction, authenticated-app interaction. Requires Chrome/Edge, extension v1.0.36+, Claude Code v2.0.73+, direct Anthropic plan. **De facto Anthropic-blessed alternative to pinchtab / Playwright MCP** for browser-tied workflows.
- **[everything-claude-code (affaan-m)](https://github.com/affaan-m/everything-claude-code)** -- "Harness performance system" bundling 60+ agents, 228+ skills, rules, hooks, and MCP configurations for Claude Code, Cursor, OpenCode, etc. Installable as Claude Code plugin or manually. **Mine for patterns** before adopting wholesale -- the agents/skills are uneven quality and the bundle is large.
- **[awesome-agent-skills (VoltAgent)](https://github.com/VoltAgent/awesome-agent-skills)** -- Curated index of 1,100+ agent skills from official teams (Anthropic, Google, Vercel, Stripe) and community contributors. Targets Claude Code, Codex, Gemini CLI, Cursor. Browse before writing a new skill from scratch.
- **[AgentHub (jamesrochabrun)](https://github.com/jamesrochabrun/AgentHub)** -- Native macOS app (SwiftUI) for managing Claude Code and Codex CLI sessions: real-time monitoring, parallel terminal execution, integrated diffs, worktree creation, GitHub PR/issue browsing. Worth a look when juggling many parallel agent sessions exceeds tmux's ergonomics.
- **[Anthropic Academy (Skilljar)](https://anthropic.skilljar.com/)** -- Anthropic's official training portal with 20+ courses on Claude tools, API, MCP, agent skills, and AI fluency. Skim for non-obvious capabilities -- this is "how Anthropic wants you to use Claude," authoritative.

### AI coding agents -- alternatives to evaluate against Claude Code / Codex / Cursor

> User research note (2026-04-30): "read on OpenHands; OpenCode; Aider meh against Claude Code / Codex / Cursor"

- **[OpenHands](https://github.com/All-Hands-AI/OpenHands)** (formerly OpenDevin) -- OSS autonomous coding agent that runs in a sandboxed Docker environment. Multi-model, supports Anthropic / OpenAI / local. Worth comparing for the "fully autonomous agent in a sandbox" workflow.
- **[OpenCode](https://github.com/opencode-ai/opencode)** -- OSS terminal coding agent. Lightweight, BYO API key. Compare against Aider for cost-control / provider-flexibility use cases.
- **[Aider](https://aider.chat/)** -- Veteran OSS terminal coding agent. User flagged "meh" in 2026-04 notes -- worth confirming whether the gap to Claude Code / Codex has actually closed or remained.
- **[Codex CLI](https://github.com/openai/codex)** (the actual CLI, distinct from Claude Code / Cursor) -- OpenAI's official terminal coding agent. The cross-model pairing pattern: write with Claude Code, review with Codex (or reverse).

### Observability / Analytics

- **[PostHog](https://posthog.com/)** -- Product analytics + session replay + feature flags + A/B + LLM observability all in one. User note (2026-04): "PostHog wiki has tips" -- worth a skim for both feature-flag patterns and the LLM observability dashboards. OSS self-hostable; cloud also offered.

- **[ChatGPT Atlas (OpenAI)](https://chatgpt.com/atlas)** -- OpenAI's AI-native browser (launched late 2025). ChatGPT is the default address bar / sidebar / agent on every page; reads what's on screen and can take actions (form fill, navigation, multi-tab workflows) inside an authenticated browser session. Mentioned in Garry Tan's "20x Company" video as part of the toolchain that lets tiny teams operate at scale. Compare against **Claude in Chrome** (already tracked) -- Atlas is a *whole browser*, Claude in Chrome is an *extension on top of Chrome*. The browser-as-product positioning makes Atlas more aggressive about agent context (sees everything) and more concerning for privacy boundaries. Worth evaluating side-by-side if browser automation is core.

### Research & comparison sources

- **[Artificial Analysis](https://artificialanalysis.ai/)** -- Independent LLM benchmarking. Quality vs. price vs. speed scatter plots for every frontier model, and per-provider latency/throughput tables. The fastest way to answer "what's the best model under $X/M tokens right now?" Bookmark for model-selection decisions and Kimi/DeepSeek/Qwen comparison runs.
- **[Arena.ai Leaderboard](https://arena.ai/leaderboard)** -- Crowd-sourced human-preference Elo rankings (successor to Chatbot Arena/LMSYS). Distinct tabs for Text, WebDev, Vision, Document, Search, Image, Video. Most useful for "which model do humans actually prefer for X?" -- orthogonal to AA's quantitative benchmarks. Cross-reference both before committing to a default model.
- **[Hermes Guide -- AI Models](https://hermesguide.xyz/ai-models/)** -- Curated model directory with capability tags, context window, and provider routing notes. Complements Artificial Analysis (Hermes leans editorial; AA leans quantitative).
- **[deepseek-ai/awesome-deepseek-agent](https://github.com/deepseek-ai/awesome-deepseek-agent)** -- Official curated index of agent frameworks that integrate DeepSeek (Claude Code, Codex, opencode, Pi, Crush, Kilo Code, Hermes, Reasonix, DeepSeek-TUI, …). Use as the canonical source when wiring a non-Anthropic/non-OpenAI model into one of our existing harnesses.

### Cheap inference for Kimi & DeepSeek (2026-05 snapshot)

Use one of the third-party hosts below if Moonshot's / DeepSeek's first-party APIs are rate-limited, geo-restricted, or you want unified billing. Prices listed are USD per million tokens (input / output).

- **DeepSeek V3.2** -- First-party DeepSeek API is cheapest at the source (~$0.07 cached / $0.27 standard input, $0.41 output). On **[OpenRouter](https://openrouter.ai/deepseek/deepseek-v3.2/providers)**: ~$0.25 / $0.38, 131K context, route via OR's load balancer to fall back across Fireworks/DeepInfra/Novita. **[Fireworks](https://fireworks.ai)** lists DeepSeek V3.2 at $0.56 / $1.68 with sub-second TTFT. For coding/agentic loops, prefer OpenRouter for failover; for pure cost, go direct to DeepSeek's `platform.deepseek.com`.
- **Kimi K2 / K2.5** -- Moonshot's own [platform.kimi.ai](https://platform.kimi.ai/docs/pricing/chat) is competitive (~$0.60 / $2.00 for K2.5). Third-party: **[DeepInfra](https://deepinfra.com)**, **[OpenRouter](https://openrouter.ai)**, **[Together](https://together.ai)**, **[Fireworks](https://fireworks.ai)** all host K2 and K2.5. K2 (non-thinking) is the cheapest path; K2.5 / K2.6 add reasoning at ~3-4× the output cost. Use the **[Artificial Analysis providers page for Kimi K2](https://artificialanalysis.ai/models/kimi-k2)** for a live price table.
- **Routing strategy:** wire Kimi/DeepSeek into the **OpenRouter** account that's already used for ad-hoc routing. One API key, unified billing, automatic provider failover. Tradeoff is a 5-10% margin vs. going direct. For agent-heavy use where latency matters more than cost, use Fireworks; for cost-floor batch jobs, use DeepInfra or DeepSeek/Moonshot direct.
- **Local fallback:** both Kimi K2 (1T params, MoE) and DeepSeek V3 (671B, MoE) are too large for a single M4 Pro. Distilled variants (Kimi-K2-mini, DeepSeek-V3-Lite) run via **Ollama** or **LM Studio** if local inference becomes load-bearing -- currently disabled in `macos/brew.sh`.

## AI Stack Rankings (personal, 2026-05)

> Hands-on ordering, not benchmarks. Feeds [ADR-0004](adr/0004-local-ai-stack-and-barbell-inference.md) (barbell inference, Zed default, ~3-tool workflow). Some entries still TBD as evaluation continues.

### Model access

**Self-hosted runners** — 1. **LM Studio** (MLX, best on Mac; powers the editors). 2. **Jan** (solid 2nd; better if you're *not* also powering other editors). 3. **Msty** (fine, no winning niche yet). *Honorable mention:* **Ollama** (fine; LM Studio edges it on Mac — disabled in `brew.sh`).

**Paid inference hosts** — **no niche for this profile** (barbell: local OR subsidized frontier). Tried none; would only revisit for sustained parallel automation, no-rate-limit batch, or a too-big-for-laptop model cheaper than frontier. Players: OpenRouter (router/failover), Together (incl. FP4), Fireworks, DeepInfra, Novita, Parasail, Baseten, Hyperbolic, Clarifai, Eigen AI, Groq, Cerebras, CoreWeave, Cloudflare Workers AI, AWS Bedrock, Google Vertex. Snapshot leaders (May 2026): fastest + lowest-latency = **Together FP4**; lowest price = **DeepInfra FP4 / Parasail**.

**Closed frontier APIs** — 1. **Anthropic**. 2. **OpenAI**. 3. **Google** (for now). No other closed-only provider currently of interest.

### Harnesses

**Proprietary CLIs / apps** — 1. **Claude Code / Claude Desktop**. 2. **Codex CLI / Codex Desktop**. 3. **Gemini CLI** (no desktop; lagging on model quality).

**Model-variety IDEs** — **Zed** wins heavily (model range + vibe) ≫ **Cursor** (undeniably great; lingering personal aversion).

**Model-variety CLIs** — **OpenCode** leads on mindshare / feature parity, but the *whole concept* is undercut while proprietary CLIs subsidize inference via subscription. Then **Crush**. **Goose** ranks lowest of those tried (see niche below). **Pi** TBD.

**Overall daily-driver feel** — 1. (tie) **Zed** (flexible; shows code, not just an agent REPL) and **Pi** (pi.dev — surprisingly delightful: ultra-light terminal agent, ~1k-token system prompt, hackable, mid-session provider swap). 2. **Claude Code / Codex CLI / Cursor (+Cursor CLI)**. 3. **Gemini CLI**. 4. **OpenCode**. 5. **Crush** (cute, but the glamorous TUI is both nice and way too much — "just build an IDE if you're going to be so heavy"). 6. **Goose** (lowest of tools tried — see below). opencode/crush both fine, just too heavy for a daily driver vs a real IDE.

> **Pi's niche here:** terminal-native lightweight loop for **local LM Studio** (free/private) and BYO-key provider-hopping with a consistent feel — complements Zed (editor/diff surface) rather than competing. Caveat: Pi can't ride the Claude **Max** subscription — Anthropic OAuth in third-party harnesses is metered/pay-per-token (ToS-gray), so frontier-on-subscription stays in Zed-ACP / Claude Code. See [ADR-0004](adr/0004-local-ai-stack-and-barbell-inference.md).

> **Warp** (warp.dev) — WATCH, not yet tried. Different direction: an AI-native *terminal* built for multi-agent dev (Codex/OpenCode/Gemini as first-class threads, per-agent worktree/branch/PR metadata, unified notifications). Solid-feeling, ambitious product; a plausible "great solution" — deferred while exploring Zed. Revisit if juggling many agent sessions outgrows Zed + Ghostty.

> **Goose (Block → Linux Foundation/AAIF) — WATCH, no use today.** Targeted niche is **autonomous execution / headless automation** ("Recipes" — fire-and-let-it-work, install/run/edit/test), *not* the interactive, watch-every-tool transparency this setup values. First hands-on was poor: the CLI is deliberately plain (no rich TUI, no message queue), shows little with no extensions enabled, and a 4B local model can't tool-call reliably. Revisit only if a headless/scheduled automation need appears — then try Goose **Desktop** + the Developer extension + a frontier model, not the bare CLI.

## AI Tooling Research Notes (2026-05)

Findings from a deep research pass (2026-05-25). Sources at the end. Treat dollar figures and limits as accurate-as-of-late-May-2026 but volatile. We'll revisit harness benchmarking as the field matures.

### Subscription vs API access — who lets you spend a subscription in an agnostic tool

The frontier field has **bifurcated**: Western incumbents wall their subsidized subscriptions into first-party clients; challengers (Chinese labs, Cerebras, OpenAI-via-partners) compete by *welcoming* third-party tools.

| Provider | Subsidized sub exists? | Usable in 3rd-party tools (Pi / OpenCode / Zed-ACP)? | Notes |
|---|---|---|---|
| **Anthropic** | Yes (Max) | ❌ **Banned** (Jan/Feb 2026) — first-party Claude Code / claude.ai only | API key (metered) everywhere else. Confirmed via ToS + error strings. |
| **Google Gemini** | Yes | ❌ Banned; **individual CLI/IDE tiers retire Jun 18 2026** → Antigravity | As/more restrictive than Anthropic. Vertex API key for 3rd-party. |
| **OpenAI / Codex** | Yes (ChatGPT Plus/Pro) | ✅ **Officially sanctioned** (Zed native + ACP, OpenCode) — personal use | The permissive Western outlier. Zed markets this. |
| **GitHub Copilot** | Yes | ✅ Official in OpenCode (Jan 2026) | Flat today → usage-credits Jun 1 2026. |
| **Zhipu GLM** | Yes — **Coding Plan $18/mo** | ✅ Explicitly supports Claude Code/OpenCode/Cline/Cursor/Crush/Goose | The anti-Anthropic. GLM-5.1 ≈94.6% of Opus 4.6 on their eval. |
| **Alibaba Qwen** | Yes — Coding Plan ~$50/mo | ✅ via subscription endpoint+key (free OAuth ended Apr 15 2026) | Pivoted from free-OAuth to sub-key-into-tools. |
| **Cerebras Code** | Yes — $50/$200/mo | ✅ any tool, via **API key** (flat-rate hybrid) | Qwen3-Coder ~2000 t/s, no weekly limits. Best "flat + everywhere" for OSS coding. |
| **xAI Grok** | Yes (SuperGrok) | ◑ official in OpenCode; Grok Build CLI wants $99 or API credits | Mixed, leans tolerant. |
| **Moonshot Kimi** | Yes — coding plans ($39–$199) | ◑ OpenAI-compatible endpoint; subscription-passthrough ToS **gray/unverified** | Has its own Kimi Code CLI. |
| **DeepSeek** | No sub (API only) | n/a — bring cheap API key | V4-Flash ~$0.14/$0.28 per M. |
| **Mistral** | Le Chat Pro (no API) | n/a — metered API only | Consumer sub explicitly excludes API. |

**Takeaways:** Anthropic isn't unique — it's the leading edge of a Western lockdown (Google is equally/more restrictive). For our barbell: **local LM Studio (free)** or, if we ever want a sub inside an agnostic tool, **GLM Coding Plan / Cerebras / Copilot / ChatGPT** are the sanctioned paths. **Anthropic Max stays first-party** (Claude Code / Zed-ACP). Pi → Anthropic = pay-per-token API, *not* the Max sub.

### Harness benchmarking — the scaffold moves a fixed model 10–17 points

The harness (tool/scaffold) is now benchmarked **separately** from the model, and the effect is large:

- **Terminal-Bench 2.0** reports `agent+model` pairs. Same **Opus 4.7** scores **90.2%** (top harness) vs **80.2%** (a lower one) — ~10-pt spread from scaffold alone; GPT-5.5 swings ~17 pts. **Claude Code itself ranks ~51st** there.
- **LangChain** documented **+13.7 pts on one model** by changing only the harness. **SWE-Effi** (academic) and the **Aider polyglot** (edit-format efficiency) corroborate.
- **"Cursor > Claude Code on Opus 4.7"**: true on **one** published benchmark (Endor Labs: Cursor 91.1% vs Claude Code 87.2% functional) — narrow security-CVE dataset, ~4 pts. **Directionally real, not a general law.**
- **Pi**: credible-but-**unbenchmarked** (no clean published number; not on the current board). Its thesis (minimal prompt + frontier model) is plausible, not proven.
- **Zed-ACP is NOT guaranteed 1:1 with native Claude Code** — it wraps the Claude *Agent SDK*, which defaults to a *minimal* system prompt (omits Claude Code's coding guidelines) unless the `claude_code` preset is set, and shipped with plan mode / slash commands missing. So hardest work may still be marginally better in the native CLI.
- **What drives the gap:** edit/diff-format fit (#1 — models are RL'd on a specific tool surface), context management/compaction, verification-before-exit loops, reasoning-budget routing, loop detection, prompt size/structure ("model-harness fit").

> **Don't pick daily tools off the Terminal-Bench leaderboard.** The top entries (`vix`, `Capy`, `Droid`, `WOZCODE`, `Terminus 2`) are mostly **benchmark-tuned / research / competitive harness submissions** — scaffolds optimized to pass 89 terminal tasks, not consumer products with good DX. `Terminus` is the benchmark's own minimal *reference* agent. High leaderboard ≠ good daily driver; it measures scaffold-on-benchmark, not real-world ergonomics. Use it to confirm "harness matters," not to choose tools.

### Scheduling / automation portability

There is **no fully-managed vendor-agnostic agent cron.** Choices: (a) **vendor cloud** = zero ops, lock-in [Claude Routines, Codex Cloud, Cursor Automations, Jules]; or (b) **self-host a scheduler that invokes a headless agent CLI** = agnostic, you own the box.

- **Zed**: no scheduler/routines (interactive editor; hooks are editor-event-only, don't fire for agent tasks).
- **Pi**: no built-in scheduler *either*, but has the headless surfaces (`pi -p`, `--mode rpc`, SDK) to be driven by **cron / GitHub Actions / a VPS** — the agnostic path. `0 9 * * * cd /repo && pi --tools read,grep,find,ls,edit -p "$(cat nightly.md)"`.
- **Goose** has a real built-in `goose schedule` (cron) if a batteries-included open option is wanted.
- **Bottom line:** Zed + Pi *can* do scheduled runs — via Pi headless + your own trigger. The price of agnostic is hosting the runner.

### Research sources (2026-05-25)

- Subscriptions: [Anthropic OAuth ban (Register)](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/) · [Zed × ChatGPT sub](https://zed.dev/blog/chatgpt-subscription-in-zed) · [GLM Coding Plan](https://z.ai/subscribe) · [Copilot → OpenCode](https://github.blog/changelog/2026-01-16-github-copilot-now-supports-opencode/) · [Cerebras Code](https://www.cerebras.ai/blog/introducing-cerebras-code) · [Qwen free-tier shutdown](https://decrypt.co/364501/alibaba-shuts-down-free-tier-qwen-code)
- Harness benchmarking: [Terminal-Bench 2.0](https://www.tbench.ai/leaderboard/terminal-bench/2.0) · [Terminal-Bench paper](https://arxiv.org/abs/2601.11868) · [SWE-Effi](https://arxiv.org/abs/2509.09853) · [Aider edit-format leaderboard](https://aider.chat/docs/leaderboards/edit.html) · [LangChain harness engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering) · [Endor Labs (Opus 4.7)](https://www.endorlabs.com/learn/claude-opus-4-7-sets-new-records-in-the-endor-labs-agent-security-league) · [Zed Claude Code via ACP](https://zed.dev/blog/claude-code-via-acp)
- Scheduling: [Claude Routines](https://claude.com/blog/introducing-routines-in-claude-code) · [Codex Automations](https://developers.openai.com/codex/app/automations) · [Cursor Automations](https://cursor.com/docs/cloud-agent/automations) · [Jules scheduled tasks](https://jules.google/docs/scheduled-tasks/) · [Goose scheduler](https://block.github.io/goose/docs/guides/recipes/recipe-reference/)
- Pi/Zed setup: [pi.dev](https://pi.dev/) · [earendil-works/pi](https://github.com/earendil-works/pi) · [awesome-pi-agent](https://github.com/qualisero/awesome-pi-agent) · [pi-superpowers-plus](https://github.com/coctostan/pi-superpowers-plus) · [Zed external agents](https://zed.dev/docs/ai/external-agents) · [agentskills.io](https://agentskills.io)

## Cloud / Hosting Providers

Personal vibes-check on the current player set (2026-05). Opinions, not benchmarks — refine as we get hands-on.

- **Cloudflare** -- Generally a strong platform that keeps getting better (Workers, D1, R2, Pages, Queues all maturing). Some questions on the team, but the product trajectory is solid.
- **Vercel** -- Probably still a decent solution for Next.js-native frontends. Terrible place to scale (pricing traps, vendor lock-in — already flagged in `prompts/guides/services.md` "When NOT to Use"). Some questions on the team. Very AI-forward / tech-forward, so they'll keep shipping interesting things.
- **Render** -- Dark horse. Worth a real evaluation: product quality, principles/values, pricing structure. Currently filed as "budget option for simple services" in services.md but probably deserves more attention.
- **Railway** -- Seems pretty good. Possibly a little too dumbed down — TBD whether that's a feature or a ceiling. Pricing structure matters; worth scrutinizing same as Render.
- **Supabase** -- Not really a full cloud provider — they're Postgres-plus-extras (auth, storage, realtime, edge functions). Useful piece of a stack, not a primary host.
- **Google Cloud** -- Downgrade. Multiple outages recently. Reliability story is worse than the marketing suggests.
- **AWS** -- Just works, but blows in a lot of ways (UX, cost surprises, sprawl). Pick-your-poison among hyperscalers.
- **Azure** -- Same energy as AWS. Pick-your-poison.
- **Hetzner** -- The "self-rolling" option. Cheap EU bare-metal / VPS. Pair with Coolify / Dokploy / Kamal if going self-hosted PaaS. Worth a real look if cost matters or we want sovereignty from US hyperscalers.
- **Netlify** -- Curious about it but suspect they may be too small / too narrowly Jamstack to be a primary host. Worth a quick read on where they actually win vs Cloudflare Pages and Vercel.
- **Heroku** -- Hard no. Not evaluating.
- **Fly.io** -- Already in services.md as the "containers / global edge" pick. Keep on the list; reassess if pricing or reliability shifts.

- **Fly.io** -- Currently in use. Pricing is fine; probably overspending a touch right now and worth a right-sizing pass (check machine sizes, suspended-vs-stopped, Postgres tier). Already in `services.md` as the containers/global-edge pick. Reassess if pricing or reliability shifts.
- **DigitalOcean** -- App Platform sits Render-adjacent (PaaS for web services); Droplets sit Hetzner-adjacent but pricier (~2–3× per vCPU/GB). Managed Postgres / Spaces / K8s are solid mid-market. Good middle ground when you've outgrown Railway/Render but don't want to live in AWS.
- **Scaleway** -- French hyperscaler-lite. Bare metal, managed K8s (Kapsule), serverless containers/functions, managed Postgres. EU sovereignty story; pricing competitive with Hetzner on bare metal. Evaluate if EU data residency matters or as a hyperscaler-light alternative to AWS.
- **OVHcloud** -- Larger / older EU player. Strong on bare metal and dedicated GPU. Console UX is rougher than Scaleway. Evaluate mainly for GPU rental or heavy bare-metal needs at EU prices.
- **Coolify / Dokploy / Kamal** -- The self-host PaaS layer that sits on top of Hetzner / DO Droplets / any VPS. **Coolify** = open-source Heroku/Vercel clone, web UI, broadest feature set. **Dokploy** = leaner Coolify alternative, more modern stack. **Kamal** (37signals/Basecamp) = CLI-only, deploys Docker containers to any SSH-able host; intentionally minimal. Pick Coolify for breadth, Dokploy if Coolify feels bloated, Kamal if you want code-as-config and no web UI. All three pair naturally with Hetzner for ~5–10× cost reduction vs Railway/Render at small-to-mid scale.
- **Northflank** -- Kubernetes-native PaaS that hides the K8s. Build, deploy, autoscale services, jobs, databases, GPUs in one platform. BYOC mode (run on your own AWS/GCP/Azure account) is the killer feature: PaaS DX without vendor lock-in, and you can negotiate hyperscaler commits. Pricing roughly Railway-level on their cloud; on BYOC you pay hyperscaler costs + a margin. Strongest candidate when you outgrow Railway but want to stay off raw K8s.
- **Porter** -- Similar shape to Northflank: PaaS-on-top-of-K8s, BYOC-first (deploys into your AWS/GCP). Heroku-style git push deploys. More opinionated than Northflank, smaller surface. Evaluate head-to-head with Northflank if BYOC K8s is the goal.

### Scaling up — enterprise-level + good cost (2026-05 take)

Picking by stage and constraint, since "best" depends on what you're optimizing:

- **Best raw $/perf if you can self-manage:** Hetzner + Coolify (or Kamal for code-as-config). Brutal cost advantage; you own the ops burden. Good for serious scale if you have someone who likes infra.
- **Best PaaS DX without lock-in at scale:** Northflank BYOC into AWS or GCP. You get Railway-grade DX, but the underlying resources are your hyperscaler account — so you can negotiate enterprise commits, satisfy compliance, and exit if needed.
- **Best edge-native + flat pricing at scale:** Cloudflare. Workers + D1 + R2 + Queues + Durable Objects. Egress is free (huge), R2 has no egress fees vs S3, D1 has predictable per-request pricing. Weakness: long-running compute and big-RAM workloads are awkward.
- **Best if you must be on a hyperscaler:** AWS via SST (already the services.md default for TS). Pick AWS if compliance / partner ecosystem / enterprise sales demand it; otherwise the cost story is worse than the alternatives above.
- **Avoid for "serious scale":** Vercel (pricing traps), Railway (ceiling unclear, less BYOC story), Heroku (don't).

Rough mental model: **Hetzner+Coolify** for cost-floor self-host, **Northflank BYOC** for PaaS-DX-at-enterprise, **Cloudflare** for edge-native, **AWS+SST** for compliance/ecosystem reasons. Most serious shops end up running 2 of these.

### Specialist data layer (when to pick over a full provider's DB)

The question of "PlanetScale vs Neon vs Turso vs Cloudflare D1 vs Supabase Postgres vs Fly Postgres" comes down to **workload shape**, not vendor preference:

- **[PlanetScale](https://planetscale.com)** -- MySQL (Vitess) with horizontal sharding, branching, and online schema changes. Removed their free tier in 2024 (~$39/mo entry), so this is a "we're serious about MySQL at scale" pick now. Best when you need MySQL specifically, true horizontal sharding, or zero-downtime schema migrations on a hot table. Overkill for most apps.
- **[Neon](https://neon.tech)** -- Serverless Postgres with branching and scale-to-zero. Free tier exists; paid starts ~$19/mo. Storage and compute billed separately, which makes per-tenant / per-PR-branch usage cheap. Best when you want real Postgres with dev/preview branching, infrequent workloads, or many small databases. The "Vercel-Postgres" backend used to be Neon under the hood.
- **[Turso](https://turso.tech)** -- libSQL (SQLite fork) with multi-region replicas, per-database isolation, scale-to-zero. Free tier generous; paid scales with row reads / storage. Best for edge-read-heavy workloads, per-tenant isolated databases (multi-tenant SaaS where each customer = one DB), or anything where sub-10ms reads at the edge matter more than complex SQL. Weak on heavy writes and complex joins.
- **Cloudflare D1** -- Cloudflare's managed SQLite. Tight integration with Workers; included generously in the Workers paid plan ($5/mo). Per-request and per-row-read pricing, cheap at small-to-mid scale. Best when you're already all-in on Cloudflare and the data fits SQLite semantics. Weaker tooling and ecosystem than Turso (no libSQL extensions, fewer ORMs) but the integration story with Workers/Pages is unbeatable.
- **Supabase Postgres** -- Real Postgres + auth + storage + realtime + edge functions in one product. Pick when you want a batteries-included BaaS, not when you want a focused database. Pricing reasonable up to ~$25/mo Pro; scales linearly past that.
- **Fly Postgres** -- Just Postgres on Fly machines. Cheap, you-manage-it. Fine for app-and-DB-on-same-platform but no autoscale or branching magic.

**Decision rule of thumb:**
- Need MySQL at scale or zero-downtime migrations → PlanetScale
- Need Postgres with branching / preview envs / scale-to-zero → Neon
- Need per-tenant isolated DBs or edge reads → Turso
- Already on Cloudflare and data is SQLite-shaped → D1
- Want a full BaaS, not just a DB → Supabase
- Already on Fly, just need Postgres → Fly Postgres
- On AWS for compliance → RDS / Aurora Serverless v2 (boring, expensive, works)

Open questions to chase next round: Render pricing + principles, Railway scaling ceiling, Hetzner + Coolify/Dokploy stack, Netlify's real niche in 2026, Northflank BYOC pricing on AWS vs raw EKS, Fly right-sizing pass.

## Home / Personal

- **[Scrypted](https://github.com/koush/scrypted)** -- Home automation platform. Evaluate as a HomeKit / NVR alternative.

## Reference Reading

- **[Building a CLI for all of Cloudflare](https://blog.cloudflare.com/cf-cli-local-explorer/)** -- How Cloudflare approached building a unified CLI. Useful if we ever build a CLI across services.

## Other

- **Project Glasswing** -- Amazon's rumored internal AI agent framework. Track for potential public release or competitive implications.
