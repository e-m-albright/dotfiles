# Python Stack

**Philosophy**: Fast, type-safe Python for APIs, ML services, and automation.

## Runtime & Tooling

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Package Manager** | UV | pip is slow, poetry is complex. UV is 10-100x faster, Rust-based, modern lockfile. |
| **Python Version** | 3.12+ | 3.11 is stable but 3.12 has better typing, faster startup. |
| **Linter** | Ruff | flake8/pylint are slow, need plugins. Ruff is 10-100x faster, replaces multiple tools. |
| **Formatter** | Ruff | Black is good but Ruff does both in one tool. |
| **Type Checker** | Pyright | mypy is slower, less accurate. Pyright (via Pylance) is faster, stricter. |
| **Task Runner** | Just | Makefiles are arcane. Just is readable, cross-platform. |

## Framework

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Web Framework** | FastAPI | Flask lacks async, Django is heavy. FastAPI is async-native, auto-docs, type-safe. |
| **ASGI Server** | Uvicorn | Gunicorn is WSGI-only. Uvicorn is async, works with FastAPI. |
| **Validation** | Pydantic v2 | Attrs is good but Pydantic has better FastAPI integration, v2 is 5-50x faster. |

## Database & Data

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **ORM** | SQLAlchemy 2.0 | Django ORM is Django-only. SQLAlchemy is industry standard, async support. |
| **Migrations** | Alembic | Built for SQLAlchemy, reliable, widely used. |
| **Database** | PostgreSQL | SQLite lacks concurrency. Postgres is the production standard. |
| **Async Driver** | asyncpg | psycopg2 is sync-only. asyncpg is native async, fastest PostgreSQL driver. |

## Testing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Framework** | pytest | unittest is verbose. pytest is simpler, better fixtures, plugins. |
| **Coverage** | pytest-cov | Built-in, works with pytest. |
| **Async Testing** | pytest-asyncio | Native pytest integration for async tests. |
| **Mocking** | pytest-mock | Thin wrapper around unittest.mock, cleaner API. |
| **HTTP Mocking** | respx | responses is sync-only. respx works with httpx async. |

## HTTP & APIs

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **HTTP Client** | httpx | requests is sync-only. httpx supports async, same API. |
| **API Docs** | OpenAPI (built-in) | FastAPI generates OpenAPI automatically. |

## ML/Data (Optional)

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **DataFrames** | Polars | Pandas is slow. Polars is 10-100x faster, better API. |
| **ML Framework** | PyTorch | TensorFlow is declining. PyTorch is research standard. |
| **Experiment Tracking** | Weights & Biases | MLflow is self-hosted complexity. W&B is better UX. |

## Dev Experience

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Notebooks** | Marimo | Jupyter has reproducibility issues. Marimo is reactive, git-friendly. |
| **Documentation** | MkDocs + Material | Sphinx is complex. MkDocs is simpler, Material theme is modern. |
| **Pre-commit** | Lefthook | pre-commit is Python-based, slower. Lefthook is Go, parallel. |

---

## Version Requirements

```toml
[project]
requires-python = ">=3.12"

[tool.uv]
python = "3.12"
```

## Critical Notes

1. **UV over pip**: Always use `uv pip install` or `uv sync` — never raw pip
2. **Pydantic v2**: Use `from pydantic import BaseModel` — v2 API is different from v1
3. **SQLAlchemy 2.0**: Use new 2.0-style queries — `select()` not `session.query()`
4. **Async by default**: Use `async def` for route handlers and database operations
5. **Type hints everywhere**: Use `from typing import` — Pyright enforces strict mode
