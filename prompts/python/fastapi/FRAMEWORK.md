# FastAPI

---

## Quick Reference

```yaml
Framework:   FastAPI + Uvicorn
Database:    SQLAlchemy 2.0 + asyncpg + Atlas
Agents:      PydanticAI + Instructor
```

---

## Commands

```bash
# Development
just dev                   # Start dev server
just shell                 # Open Python shell with env

# Database
just db-migrate            # Run migrations
just db-upgrade            # Generate + run migrations
just db-downgrade          # Rollback one migration
```

---

## Project Structure

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── config.py          # Settings via pydantic-settings
│   ├── deps.py            # Dependency injection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/        # Route handlers
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   └── users.py
│   │   └── deps.py        # Route-specific dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py    # Auth utilities
│   │   └── errors.py      # Custom exceptions
│   ├── models/            # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/           # Pydantic schemas
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   └── user.py
│   └── db/
│       ├── __init__.py
│       ├── session.py     # Database connection
│       └── schema.sql     # Atlas schema (or migrations/)
tests/
├── conftest.py            # Shared fixtures
├── test_api/
└── test_services/
```

---

## FastAPI Route

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user."""
    service = UserService(db)
    user = await service.create(data)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user by ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)
```

---

## SQLAlchemy Model

```python
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """User database model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

## Service Layer

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password


class UserService:
    """User business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
```

---

## Database Session

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

## Test Fixture

```python
# tests/conftest.py
import pytest
from collections.abc import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

---

## Exception Handler

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.core.errors import AppError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
```

---

## PydanticAI Agent Pattern

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from httpx import AsyncClient

class Dependencies(BaseModel):
    """Dependencies injected into agent tools."""
    http_client: AsyncClient
    api_key: str

class WeatherResult(BaseModel):
    """Structured output from weather agent."""
    location: str
    temperature: float
    conditions: str

weather_agent = Agent(
    "openai:gpt-4o",
    deps_type=Dependencies,
    result_type=WeatherResult,
    system_prompt="You are a weather assistant. Use the get_weather tool to fetch data.",
)

@weather_agent.tool
async def get_weather(ctx: RunContext[Dependencies], location: str) -> str:
    """Fetch weather data for a location."""
    response = await ctx.deps.http_client.get(
        f"https://api.weather.com/v1/current",
        params={"q": location, "key": ctx.deps.api_key},
    )
    return response.text

# Usage
async def main():
    async with AsyncClient() as client:
        deps = Dependencies(http_client=client, api_key="...")
        result = await weather_agent.run("What's the weather in Tokyo?", deps=deps)
        print(result.data)  # WeatherResult(location="Tokyo", ...)
```

---

## Critical Rules (FastAPI)

### Always

- Use `async def` for route handlers and database operations
- Use dependency injection via `Depends()`

### Never

- Use `time.sleep()` in async code — use `asyncio.sleep()`
