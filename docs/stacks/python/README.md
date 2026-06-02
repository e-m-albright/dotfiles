# Python

> Curated taste, not mandate — read this to derive per-project choices.

## Selection (pick / avoid / by phase)

### Phase 1 — every project

| Category | Pick | Avoid |
|----------|------|-------|
| Package manager | **uv** | pip (slow), Poetry (complex) |
| Python version | **3.14** | older versions |
| Lint + format | **Ruff** (one tool) | Black + isort + flake8 (three tools) |
| Type checker | **ty** (Astral) — advisory; **Pyright strict** blocking | mypy (slower) |
| Task runner | **Just** | Make (arcane) |
| Git hooks | **Lefthook** | Husky, pre-commit |
| Logging | **structlog** | stdlib `logging`, Loguru |

Ruff target stays `py313` until Ruff supports 3.14.

**Type checker, in practice:** `ty` is the direction (Rust-fast, Astral-made) but is pre-1.0. Until it reaches 1.0 with strict-mode parity (notably overload/generic inference), run **Pyright strict as the blocking gate** and `ty` advisory alongside. Flip ty to blocking once it clears that bar. Pyright's Node dependency is the price of a mature strict checker today.

### Phase 2 — when needed

| Need | Pick | Avoid |
|------|------|-------|
| Web API | **FastAPI** (async-native) | Flask (no async), Django (heavy) |
| ORM | **SQLAlchemy 2.0** | SQLModel (maintenance mode), Django ORM |
| Migrations | **Atlas** | Alembic (slower DX) |
| Async Postgres driver | **asyncpg** | psycopg2 (sync) |
| Validation | **Pydantic v2** | marshmallow, attrs |
| Background jobs | **Arq** | Celery (complex, sync-first) |
| Durable workflows | **DBOS** (library, Postgres-only) | hand-rolled retry/checkpoint loops |
| Retries | **stamina** | tenacity (older API), hand-rolled backoff |
| CLI tools | **Typer + Rich** | Click (verbose), argparse |
| HTTP client | **httpx** (async) | requests (sync-only) |
| AI agents | **PydanticAI** | LangChain (bloated) |
| Structured LLM output | **Instructor** (or PydanticAI's native `output_type`) | — |
| MCP server | **FastMCP** | raw MCP SDK (verbose) |
| Full-stack app | **Reflex** | Streamlit (limited), Dash (verbose) |

**Jobs vs. durable workflows:** reach for **Arq** for simple background jobs (one-shot, retryable). When a *multi-step* workflow must survive a crash and resume from the last completed step (and not re-run side effects), that's durable execution — **DBOS** is the lightweight default (a library that checkpoints to your existing Postgres, no new infra); **Temporal** is the heavy-duty escape hatch when correctness-at-scale genuinely demands a cluster. See [services.md](../services.md#durable-execution--workflows).

### Phase 3 — at scale

| Need | Pick | Notes |
|------|------|-------|
| DataFrames | **Polars** | not Pandas (slow, memory-hungry) |
| Analytics SQL | **DuckDB** | in-process OLAP on Postgres/Parquet |
| Observability | **OpenTelemetry** | once 2+ services |
| Property testing | **Hypothesis** | edge-case coverage |
| Profiling | **Scalene** | CPU + memory + GPU simultaneously |
| Notebooks | **Marimo** | reactive, git-friendly (.py files); not Jupyter (reproducibility issues) |
| Docs | **MkDocs + Material** | not Sphinx (complex) |

### Testing toolkit

The test runner is **pytest**. Round it out with:

| Need | Pick | Notes |
|------|------|-------|
| Test data factories | **Polyfactory** | Type-hint-driven; pydantic validators still run, so it can't emit invalid data. Beats hand-written fixtures and factory_boy |
| HTTP mocking | **respx** | Mock httpx at the transport layer |
| Snapshot testing | **inline-snapshot** (or **syrupy**) | For large dict/JSON output; regenerate-without-reading-the-diff is rubber-stamping |
| Clock control | **time-machine** | Freeze/travel time deterministically — fixes flaky time-dependent tests without widening thresholds |
| Property testing | **Hypothesis** | (also in Phase 3) edge-case coverage |
| API fuzzing | **schemathesis** | OpenAPI-driven property/fuzz testing — near-free defect-finding if you have a spec |
| Mutation testing | **mutmut** | Periodic audit of test *quality* on critical modules — not an always-on gate |
| Parallel / coverage | **pytest-xdist**, **pytest-cov**, **pytest-benchmark** | `-n auto --dist loadfile`; gate bench regressions in CI with **CodSpeed** |

### Don't install

| Tool | Why skip |
|------|----------|
| mypy | ty/Pyright cover it; mypy is slower |
| Black / isort | Ruff does both |
| Loguru | structlog is the one logger |
| SQLModel | maintenance mode |
| Alembic | Atlas wins on DX |

> **Beartype** is *not* an anti-pick: Pydantic validates at trusted boundaries, but **beartype** adds cheap runtime type enforcement on *internal* boundaries Pydantic doesn't reach (plain functions, dataclasses). Reach for it via a `@validate_types`-style decorator on hot internal interfaces when you want runtime teeth to back the static checker.

### Performance swaps (hot paths)

Drop-in, API-compatible replacements. Reach for these when profiling shows the stdlib version is a bottleneck — the swap cost is small.

- **uvloop** — libuv-based asyncio event loop (~2–4× faster I/O). `uvloop.install()` at app entry. Auto-detected by Uvicorn; native in Granian. Not Windows-compatible.
- **orjson** — Rust JSON encoder/decoder (2–5× faster than stdlib `json`, fewer footguns on dates/UUIDs). Returns `bytes`, not `str`. Use for serialization hot paths; via `ORJSONResponse` for FastAPI.
- **Granian** — Rust ASGI/WSGI/RSGI server. Lower per-request overhead and faster startup than Uvicorn/Gunicorn. Pick for production where p99 latency matters; Uvicorn is fine for dev.
  ```bash
  granian --interface asgi app.main:app --workers 4
  ```

## Idioms

- **uv when `uv.lock` is present** — never fall back to `pip install`. `pyproject.toml` is the single source of truth; use `uv add`, `uv run`, `uv sync`.
- **Ruff for lint and format** — don't introduce Black, isort, or flake8 alongside it. Run `ruff check --fix` and `ruff format` scoped to changed files.
- **Type-annotate all function signatures.** Modern union syntax `str | None` (not `Optional[str]`); lowercase builtins `list[str]`, `dict[str, int]` (not `List`, `Dict`); `from collections.abc import Callable, Sequence, Mapping`.
- **Pydantic v2 syntax**: `model_config = ConfigDict(...)`, not `class Config:`.
- **SQLAlchemy 2.0 syntax**: `select()`, not `session.query()`.
- **`async def` for I/O, `def` for pure functions.** Never `time.sleep()` in async code — use `asyncio.sleep()`.
- **Guard clauses and early returns** over deep nesting.
- **`pathlib.Path` over `os.path`** for file operations.
- **structlog for logging** — never stdlib `logging` or `loguru`, never `print()` in production.
- **`dataclass` for internal data structures, Pydantic for external/API data.** Pydantic models validate all external data.
- **Config via Pydantic Settings** (`BaseSettings`) as the single config source, accessed through an `@lru_cache` singleton. No inline `os.getenv()` in business logic — all config flows through the settings object.

### Async

- Prefer `asyncio.TaskGroup()` over `asyncio.gather()` — structured concurrency, proper cancellation.
- `asyncio.Semaphore` to bound concurrent external calls.
- Correlate requests via an `X-Request-ID` header + `contextvars.ContextVar`.

### Avoid

- `Any` — use specific types.
- Mutable default arguments (`def f(items: list = [])`) — default to `None` and build in the body.
- `from x import *` — always explicit imports.
- Bare `except` or `except Exception` without re-raise — be specific. At minimum, log caught errors (`structlog.get_logger().warning(...)`); never catch-and-ignore silently.
- `isinstance` chains — use `match`/`case` or polymorphism.

## Code patterns

### Cross-cutting concerns via decorators

Keep business logic clean; push orthogonal behavior into decorators.

```python
@timed("operation_name")                # OTEL span with duration
@retry(on=httpx.TransportError)         # stamina retry with structlog
@cached(TTLCache(maxsize=256, ttl=300)) # cachetools TTL cache
```

### Modern type hints

```python
# | for unions (3.10+)
def process(value: str | None) -> str | None: ...

# lowercase builtins (3.9+)
def get_items() -> list[str]: ...

# collections.abc for abstract types
from collections.abc import Callable, Sequence, Mapping
```

### Performance defaults at app entry

```python
import uvloop
uvloop.install()  # before the event loop / app starts
```

### Common commands

```bash
uv sync                 # install dependencies
uv run pytest           # run tests
uv run ruff check .     # lint
uv run ruff format .    # format
uv run ty check         # type check
```

## Project layout

```
src/app/
├── main.py           # app entry
├── config.py         # pydantic-settings
├── api/routes/       # route handlers
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # business logic
└── db/
    ├── session.py    # database connection
    └── migrations/   # Atlas
```

## See also

- [ml.md](ml.md) — ML / data-science stack and idioms
- [frameworks/fastapi.md](frameworks/fastapi.md) — FastAPI patterns
- [../../engineering-philosophy.md](../../engineering-philosophy.md) — universal code-health principles
