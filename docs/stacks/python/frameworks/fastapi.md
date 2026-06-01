# FastAPI

> Curated taste, not mandate — read this to derive per-project choices.

## Selection

```yaml
Framework:   FastAPI + Uvicorn (dev) / Granian (prod)
Event loop:  uvloop (auto-picked by Uvicorn, native in Granian)
JSON:        orjson via ORJSONResponse
Database:    SQLAlchemy 2.0 + asyncpg + Atlas
Validation:  Pydantic v2
Agents:      PydanticAI + Instructor
```

FastAPI over Flask (no async) or Django (heavy). See [../README.md](../README.md) for the full stack rationale.

## Idioms

- **`async def` for all route handlers and database operations.** Never `time.sleep()` in async code — use `asyncio.sleep()`.
- **Dependency injection via `Depends()`.** Use `Annotated` for clean signatures: `DBSession = Annotated[AsyncSession, Depends(get_db)]`.
- **Service layer between routes and the database** — routes never query directly. The same service functions back both API routes and MCP tools.
- **Separate Pydantic schemas per resource**: `Create`, `Update`, `Response`. Use `model_config = ConfigDict(from_attributes=True)` for ORM → schema conversion.
- **SQLAlchemy 2.0 style**: `select()` + `result.scalar_one_or_none()`, never `session.query(...)`.
- **`expire_on_commit=False`** on async sessions.
- **Register exception handlers** for custom `AppError` types and return a standard envelope: `{"error": {"code": "NOT_FOUND", "message": "..."}}`.
- **Performance defaults on every new app**: `uvloop.install()` before start, and `default_response_class=ORJSONResponse`. Serve prod with Granian; dev with Uvicorn.

## Code patterns

### Performance defaults

```python
import uvloop
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

uvloop.install()  # before app starts
app = FastAPI(default_response_class=ORJSONResponse)
```

Prod: `granian --interface asgi app.main:app --workers <N>`. Dev: Uvicorn is fine.

### Route handler (service layer + error envelope)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user by ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
```

### Pydantic v2 schema (ORM mode)

```python
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)  # enable ORM mode

    id: int
    email: str
    name: str
```

### SQLAlchemy 2.0 model

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
```

### SQLAlchemy 2.0 query

```python
from sqlalchemy import select

# 2.0 style (correct)
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# 1.x style (wrong — do not use)
# user = db.query(User).filter(User.id == user_id).first()
```

### Async database session

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

## Testing

- `pytest` + `pytest-asyncio` + `httpx.AsyncClient` with `ASGITransport`.
- Transactional fixtures: create tables, yield session, roll back.
- Override the `get_db` dependency in tests.

## MCP integration

When exposing functionality to Claude Desktop or other MCP clients:

- Use **FastMCP** to define MCP tools alongside the FastAPI app.
- Share the service layer — MCP tools and API routes call the same service functions.
- Keep MCP tool definitions thin (like routes): validate input, call service, return result.

## Project layout

```
src/app/
  main.py                  — FastAPI app entry point
  config.py                — Settings via pydantic-settings
  deps.py                  — Dependency injection
  api/routes/              — Route handlers
  models/                  — SQLAlchemy models
  schemas/                 — Pydantic schemas (Create, Update, Response)
  services/                — Business logic
  core/errors.py           — Custom exceptions
  db/session.py            — Database connection
tests/
  conftest.py              — Shared fixtures (async client, db session)
```

## Commands

```bash
just dev          # start dev server
just test         # run tests
just check        # lint + typecheck + test
just db-migrate   # run migrations
```

## See also

- [../README.md](../README.md) — Python stack, idioms, performance swaps
- [../ml.md](../ml.md) — ML / data-science stack
