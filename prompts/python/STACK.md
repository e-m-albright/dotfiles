# Python Stack

**Philosophy**: Fast, type-safe Python for APIs, AI services, analytics, and full-stack apps.

> **Note**: This is a menu, not a mandate. Pick what you need for your specific project.
> A simple script needs UV and maybe Typer. An API needs FastAPI. Analytics needs Polars.
> Don't install everything — add tools as requirements emerge.

---

## Installation Phases

Tools are grouped by when to add them. Start with Phase 1, add others as needed.

```
Phase 1 - ALWAYS (every project)     Phase 2 - WHEN NEEDED (specific features)
├── UV (package manager)             ├── FastAPI (APIs)
├── Ruff (lint + format)             ├── SQLAlchemy + asyncpg (database)
├── Pyright (type checking)          ├── Typer + Rich (CLI tools)
└── Just (task runner)               ├── Arq (background jobs)
                                     ├── PydanticAI (AI agents)
Phase 3 - SCALE                      └── Polars + DuckDB (analytics)
├── OpenTelemetry (2+ services)
├── Hypothesis (edge case testing)
└── Scalene (performance issues)
```

---

## Runtime & Tooling

### Phase 1: Always Install

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Package Manager** | UV | pip is slow, Poetry is complex. UV is 10-100x faster, Rust-based, handles Python versions too. |
| **Python Version** | 3.12+ | 3.12 has better typing, faster startup, improved error messages. |
| **Linter + Formatter** | Ruff | Flake8/Black/isort are 3 tools. Ruff does all, 10-100x faster. |
| **Type Checker** | Pyright | Mypy is slower, less accurate. Pyright (via Pylance) has better DX. |
| **Task Runner** | Just | Make is arcane. Just is readable, cross-platform, modern. |

### Type Checking: Pyright vs Beartype

> **Pyright**: Static analysis (catches errors before running code) — **always use**
> **Beartype**: Runtime validation (catches errors when code runs) — **rarely needed**

| Tool | When | What It Does |
|------|------|--------------|
| **Pyright** | Always | Static type checker. Catches type errors in your IDE before you run code. |
| **Beartype** | Rarely | Runtime type enforcement. Only for API boundaries where you distrust input. |

**Rule**: Pyright is mandatory. Beartype is optional and only for untrusted data boundaries (like validating external API responses). Pydantic already handles runtime validation for most use cases.

---

## Project Types

### API Services

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Web Framework** | FastAPI | Flask lacks async, Django is heavy. FastAPI is async-native, auto-docs, type-safe. |
| **Alternative** | Litestar | Faster than FastAPI, more features, but less mature ecosystem. Stick with FastAPI for now. |
| **ASGI Server** | Uvicorn | Gunicorn is WSGI-only. Uvicorn is async, production-ready. |
| **Validation** | Pydantic v2 | Built into FastAPI. v2 is 5-50x faster than v1. |

### Full-Stack Apps

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | Reflex | Streamlit is limited. Dash is verbose. Reflex is React-like in pure Python. |
| **Use Case** | Internal tools, dashboards, data apps where you don't need JS expertise. |

### CLI Tools

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **CLI Framework** | Typer | Click is verbose. Typer is Click + type hints = less boilerplate. |
| **Rich Output** | Rich | Built-in print is ugly. Rich makes beautiful terminal output trivially. |

### Background Workers

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Task Queue** | Arq | Celery is complex, sync-first. Arq is async-native, Redis-based, simpler. |
| **Alternative** | Dramatiq | More mature than Arq but sync. Use if you need reliability over async. |
| **Scheduling** | APScheduler | Simple, works with Arq. Or use system cron for basic needs. |

### Scripts & Automation

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Approach** | UV scripts | `uv run script.py` handles deps inline. No venv management needed. |
| **HTTP Client** | httpx | Requests is sync-only. httpx supports async, same API feel. |

---

## Database & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **ORM** | SQLAlchemy 2.0 | Django ORM is Django-only. SQLAlchemy is async, industry standard. |
| **Migrations** | Atlas | Alembic works but Atlas is faster, better DX, declarative schema. |
| **Database** | PostgreSQL | SQLite lacks concurrency. Postgres is production standard. |
| **Async Driver** | asyncpg | psycopg2 is sync. asyncpg is fastest async Postgres driver. |

### When PostgreSQL Isn't Enough

| Category | Choice | When to Use |
|----------|--------|-------------|
| **Analytics** | DuckDB | In-process OLAP. Query Postgres data or Parquet files blazingly fast. |
| **Time Series** | TimescaleDB | Postgres extension. Add when you need time-series optimization. |
| **Heavy Analytics** | ClickHouse | Only if Postgres + DuckDB isn't enough. Serious OLAP workloads. |

---

## Analytics & Data Science

> **Add these when you need them, not at project start.**

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **DataFrames** | Polars | Pandas is slow, memory-hungry. Polars is 10-100x faster, better API. |
| **In-Process SQL** | DuckDB | Query DataFrames, Parquet, CSV with SQL. Blazingly fast analytics. |
| **Notebooks** | Marimo | Jupyter has reproducibility issues. Marimo is reactive, git-friendly. |
| **Visualization** | Plotly | Matplotlib is verbose. Plotly is interactive, works everywhere. |

### ML/Deep Learning

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **ML Framework** | PyTorch | TensorFlow is declining. PyTorch is research standard. |
| **Experiment Tracking** | Weights & Biases | MLflow is self-hosted complexity. W&B is better UX. |

---

## Logging & Observability

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Logging** | structlog + Rich | stdlib logging is ugly. structlog is structured, Rich makes it beautiful. |
| **Configuration** | Pydantic Settings | dotenv alone doesn't validate. Pydantic Settings is type-safe env vars. |
| **Error Tracking** | Sentry | Self-hosted is complex. Sentry has excellent Python integration. |

### Observability Tiers

> **Start with Tier 1. Add tiers as complexity grows.**

| Tier | Tools | When to Add |
|------|-------|-------------|
| **Tier 1 - Essential** | structlog, Sentry | All projects. Non-negotiable. |
| **Tier 2 - Multi-Service** | OpenTelemetry | When you have 2+ services that call each other. |
| **Tier 3 - At Scale** | Jaeger, Grafana, Prometheus | When you need distributed tracing dashboards. |

### structlog + Rich Setup

```python
import structlog
from rich.console import Console

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),  # Rich-compatible
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

log = structlog.get_logger()
log.info("server_started", port=8000)
```

### OpenTelemetry Setup (Tier 2+)

```python
# Only add when you have multiple services
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup once at app startup
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to Jaeger/Grafana Tempo
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
```

---

## AI & LLM Integration

### API Clients

| Category | Choice | Notes |
|----------|--------|-------|
| **OpenAI** | openai | Official SDK, async support. |
| **Anthropic** | anthropic | Official SDK, excellent typing. |
| **Google AI** | google-generativeai | Official SDK for Gemini. |
| **Perplexity** | httpx | No official SDK; use httpx with their HTTP API. |
| **General** | litellm | Unified interface to 100+ LLMs. Good for switching providers. |

### Agent Frameworks

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Primary** | PydanticAI | LangChain is bloated, magic-heavy. PydanticAI is Pydantic-native, type-safe, minimal abstraction. |
| **Structured Outputs** | Instructor | Lightweight. Just structured outputs from LLMs, no agent complexity. |
| **Complex Multi-Agent** | LangGraph | Only when you need state machines + multi-agent orchestration. Heavy, but powerful. |

> **Start simple**: Use raw API clients + Instructor for structured outputs.
> Add PydanticAI when you need tool calling and agent loops.
> LangGraph is last resort for complex multi-agent workflows.

### PydanticAI Example

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class CityInfo(BaseModel):
    country: str
    population: int

agent = Agent(
    "openai:gpt-4o",
    result_type=CityInfo,
    system_prompt="Extract city information.",
)

result = await agent.run("Tell me about Paris")
print(result.data)  # CityInfo(country="France", population=2161000)
```

### Web Scraping & AI Crawling

| Category | Choice | When to Use |
|----------|--------|-------------|
| **AI-Native Crawling** | Firecrawl | LLM-optimized output, handles JS, bypasses blocks. Best for feeding to LLMs. |
| **Alternative** | Crawl4AI | Open-source Firecrawl alternative. Self-hosted. |
| **Search API** | Tavily | AI-optimized search API. Good for RAG pipelines. |
| **Alternative** | Exa | Semantic search API. Better for finding similar content. |
| **Browser Automation** | Playwright | When you need full browser control. Async, better than Selenium. |
| **Traditional Scraping** | Scrapy | High-volume traditional scraping. Use when AI extraction isn't needed. |

---

## Testing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | pytest | unittest is verbose. pytest is simpler, better fixtures. |
| **Async Testing** | pytest-asyncio | Native pytest integration for async tests. |
| **Property Testing** | Hypothesis | Essential for finding edge cases. Generates test inputs automatically. |
| **Mocking** | pytest-mock | Thin wrapper around unittest.mock, cleaner API. |
| **HTTP Mocking** | respx | responses is sync-only. respx works with httpx async. |
| **Coverage** | pytest-cov | Built-in, works with pytest. |

### Hypothesis Example

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs):
    """Sorting twice gives same result as sorting once."""
    assert sorted(sorted(xs)) == sorted(xs)

@given(st.text(min_size=1))
def test_reverse_reverse_is_identity(s):
    """Reversing twice returns original."""
    assert s[::-1][::-1] == s
```

---

## Debugging & Profiling

> **Add these to dev dependencies. Serious tools, not toys.**

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Print Debugging** | icecream | `print()` doesn't show context. `ic()` shows expression + value + line number. |
| **Interactive Debugger** | ipdb | pdb is ugly. ipdb has tab completion, syntax highlighting, better UX. |
| **Profiling** | Scalene | cProfile is CPU-only. Scalene profiles CPU, memory, and GPU simultaneously. |

### icecream Usage

```python
from icecream import ic

# Instead of: print(f"user_id = {user_id}")
ic(user_id)  # ic| user_id: 42

# Works with expressions
ic(len(users), users[0].name)  # ic| len(users): 5, users[0].name: 'Alice'

# Disable in production
from icecream import install
install()  # Makes ic() available everywhere
ic.disable()  # Silent in production
```

### ipdb Debugging

```python
# Drop into debugger at this line
import ipdb; ipdb.set_trace()

# Or use breakpoint() with PYTHONBREAKPOINT=ipdb.set_trace
breakpoint()

# In pyproject.toml, set default:
# [tool.pytest.ini_options]
# addopts = "--pdbcls=IPython.terminal.debugger:TerminalPdb"
```

### Scalene Profiling

```bash
# Profile entire script
scalene script.py

# Profile with web UI
scalene --web script.py

# Profile specific function
scalene --profile-only=my_module.slow_function script.py
```

---

## Infrastructure (add when needed)

### Containerization

| Category | Choice | Notes |
|----------|--------|-------|
| **Containers** | Docker | Dockerfile + docker-compose for local dev. |
| **Base Image** | python:3.12-slim | Smaller than full image. Use alpine only if size critical. |

### Infrastructure as Code

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **IaC** | Pulumi | Terraform uses HCL (another language). Pulumi uses real Python. |

### Documentation (add later, not at start)

| Category | Choice | Notes |
|----------|--------|-------|
| **Docs** | MkDocs + Material | Sphinx is complex. MkDocs is simpler, Material theme is modern. |

---

## Version Requirements

```toml
[project]
requires-python = ">=3.12"
```

## Critical Notes

1. **UV over pip**: Always use `uv pip install` or `uv sync` — never raw pip
2. **Pydantic v2 syntax**: Use `model_config = ConfigDict(...)` not `class Config:`
3. **SQLAlchemy 2.0 syntax**: Use `select()` not `session.query()`
4. **Async by default**: Use `async def` for FastAPI handlers and DB operations
5. **structlog over logging**: Structured logs are searchable and parseable
6. **Start minimal**: Don't install analytics tools for a simple API

## Quick Reference: What to Install When

### By Project Type

| Project Type | Phase 1 (Always) | Phase 2 (Add When Needed) |
|-------------|------------------|---------------------------|
| **Simple Script** | `uv` only | — |
| **CLI Tool** | + `typer`, `rich` | — |
| **API Service** | + `fastapi`, `uvicorn`, `pydantic`, `structlog`, `sentry-sdk` | — |
| **+ Database** | — | `sqlalchemy`, `asyncpg`, `atlas` |
| **+ Background Jobs** | — | `arq`, `redis` |
| **Analytics** | `polars`, `duckdb` | `marimo` (notebooks) |
| **Full-Stack App** | `reflex` | — |
| **AI/LLM Service** | `openai`/`anthropic`, `instructor` | `pydantic-ai` (tool calling) |

### Dev Dependencies

```toml
[tool.uv]
dev-dependencies = [
    # Phase 1 - Always
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "icecream",         # Better print debugging (ic() instead of print())

    # Phase 3 - When debugging/scaling
    # "hypothesis",     # Property-based testing (add when you need edge case coverage)
    # "ipdb",           # Better debugger (add when pdb isn't enough)
    # "scalene",        # CPU/memory profiler (add when you have performance issues)
]
```

### What NOT to Install

| Tool | Why Skip |
|------|----------|
| **Beartype** | Pydantic handles runtime validation. Only add if you need it at API boundaries. |
| **Loguru** | structlog is the pick. One logger per project. |
| **SQLModel** | Maintenance mode. Use SQLAlchemy 2.0 directly. |
| **LangChain** | Bloated. Use PydanticAI + Instructor instead. |
| **Alembic** | Atlas is faster, better DX. |
| **mypy** | Pyright is faster, better IDE integration. |
