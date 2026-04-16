# Tools to Evaluate

Bookmarked tools and services worth investigating.

## CI / CD

- **Blacksmith vs Deploy** -- CI provider comparison. Evaluate for cost, speed, and GitHub Actions compatibility.
- **ArgoCD** -- GitOps continuous delivery for Kubernetes. Declarative, git-driven deployments.

## Web / Frontend

- **[TanStack](https://tanstack.com)** -- Type-safe data fetching, routing, forms. Evaluate for replacing ad-hoc React data layer.
- **[Vite+](https://voidzero.dev/posts/announcing-vite-plus)** -- Next-gen build tool from VoidZero. Watch for stability and ecosystem uptake.
- **[Leptos](https://leptos.dev)** -- Rust full-stack web framework. Evaluate for Rust-heavy teams.
- **[Dioxus](https://dioxuslabs.com/)** -- Rust full-stack crossplatform app framework (web, desktop, mobile). Alternative to Leptos; evaluate when a single Rust codebase needs to ship to multiple platforms.
- **Enhance** -- Backend-first web framework. Read: [How To Build an App With Enhance](https://thenewstack.io/how-to-build-an-app-with-enhance-a-backend-first-framework/).

## CMS / Content

- **[EmDash CMS (Cloudflare)](https://www.producthunt.com/products/emdash-cms)** -- TypeScript CMS positioned as WordPress alternative. On our platform already.
- **[Payload CMS on Cloudflare Workers](https://blog.cloudflare.com/payload-cms-workers/)** -- Full-fledged CMS running entirely on Cloudflare's stack.
- **[MarkdownCMS](https://markdowncms.netlify.app/)** + **[waynesutton/markdown-site](https://github.com/waynesutton/markdown-site)** -- Lightweight markdown-driven sites.

## Editors / Terminals

- **[Zed editor](https://zed.dev)** -- Modern editor. Python support, Markdown. [Making Python in Zed Fun](https://zed.dev/blog/making-python-in-zed-fun), [Settings UI rebuild](https://zed.dev/blog/settings-ui).
- **[Ghostty 1.3.0](https://www.xda-developers.com/ghostty-13-terminal-makes-finding-your-previous-commands-a-ton-easier/)** -- Modern terminal. Improved previous-command search.

## Runtimes / Languages

- **[Bun v3.1](https://www.infoq.com/news/2026/01/bun-v3-1-release/)** -- JS runtime / bundler. Evaluate for build-step consolidation.
- **[Pyodide](https://thenewstack.io/run-real-python-in-browsers-with-pyodide-and-webassembly/)** -- Real Python in the browser via WebAssembly.
- **[Python 3.14 Lazy Annotations](https://realpython.com/python-annotations/)** -- New deferred-evaluation annotations behavior. Check impact on our typing patterns.

## Data

- **[DuckDB WebAssembly](https://www.infoq.com/news/2026/01/duckdb-iceberg-browser-s3/)** -- Query Iceberg datasets in the browser.
- **[Turso](https://thenewstack.io/why-we-created-turso-a-rust-based-rewrite-of-sqlite/)** -- Rust rewrite of SQLite. Edge-native.
- **[MotherDuck semantic layer for DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)** -- Semantic layer tutorial.

## Infra / DevOps

- **[Fly Kubernetes](https://fly.io/docs/kubernetes/)** -- Kubernetes on Fly's platform.
- **[OpenTelemetry "Demystifying OpenTelemetry" guide](https://www.infoq.com/news/2026/02/opentelemetry-observability/)** -- New OTel intro guide worth skimming before our next observability rollout.

## AI / Dev Workflow

- **[OpenSpec](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md)** -- Spec-driven dev workflow (Fission-AI). See also: [[Knowledge/Software-Engineering/Spec-Driven-Development]].
- **[Open-WebUI Open Terminal](https://github.com/open-webui/open-terminal?ref=console.dev)** -- Terminal from the Open-WebUI project.
- **[Microsoft FARA](https://github.com/microsoft/fara)** -- Microsoft agentic framework. Check positioning vs. Semantic Kernel / AutoGen.

## Home / Personal

- **[Scrypted](https://github.com/koush/scrypted)** -- Home automation platform. Evaluate as a HomeKit / NVR alternative.

## Reference Reading

- **[Building a CLI for all of Cloudflare](https://blog.cloudflare.com/cf-cli-local-explorer/)** -- How Cloudflare approached building a unified CLI. Useful if we ever build a CLI across services.

## Other

- **Project Glasswing** -- Amazon's rumored internal AI agent framework. Track for potential public release or competitive implications.
