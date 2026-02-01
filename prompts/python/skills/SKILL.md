---
name: python-fastapi-stack
description: |
  Use this skill when working with Python FastAPI projects.
  Covers: FastAPI, Pydantic v2, SQLAlchemy 2.0, async patterns, UV package manager.
---

# Python/FastAPI Stack

## When This Skill Applies

- Working with `.py` files in a FastAPI project
- Database operations with SQLAlchemy
- Pydantic schema definitions
- Async HTTP handlers
- UV package management

## Critical Patterns

### FastAPI Route Handler

```python
from fastapi import APIRouter, Depends, HTTPException, status
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

### Pydantic v2 Schema

```python
from pydantic import BaseModel, Field, ConfigDict


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode

    id: int
    email: str
    name: str
```

### SQLAlchemy 2.0 Model

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

### SQLAlchemy 2.0 Query

```python
from sqlalchemy import select

# New 2.0 style (CORRECT)
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# Old 1.x style (WRONG - don't use)
# user = db.query(User).filter(User.id == user_id).first()
```

### Async Database Session

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Type Hints

```python
# Use | for unions (Python 3.10+)
def process(value: str | None) -> str | None: ...

# Use lowercase for built-ins (Python 3.9+)
def get_items() -> list[str]: ...

# Use collections.abc for abstract types
from collections.abc import Callable, Sequence, Mapping
```

## Commands

```bash
uv sync                    # Install dependencies
uv run uvicorn app.main:app --reload  # Start dev server
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pyright             # Type check
```

## Common Mistakes to Avoid

1. **Using sync database queries** — Always use `await` with async sessions
2. **Using SQLAlchemy 1.x syntax** — Use `select()` not `session.query()`
3. **Using Pydantic v1 syntax** — Use `model_config` not `class Config`
4. **Mutable default arguments** — Never `def f(items: list = [])`
5. **Using pip directly** — Always use `uv add` or `uv pip install`

## File Structure

```
src/app/
├── main.py           # FastAPI app entry
├── config.py         # pydantic-settings
├── api/routes/       # Route handlers
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── db/
    ├── session.py    # Database connection
    └── migrations/   # Alembic
```
