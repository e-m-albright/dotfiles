# Python Style Guide

This guide covers Python patterns and framework-specific styles for FastAPI and general Python projects.

---

## Python

### Type Annotations

```python
# Always annotate function signatures
def get_user(user_id: str) -> User | None:
    ...

# Use modern union syntax (Python 3.10+)
def process(data: str | bytes) -> dict[str, Any]:
    ...

# Annotate class attributes
class Config:
    host: str
    port: int = 8080
    debug: bool = False
```

### Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator

# Use Field for validation and documentation
class CreateUserRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=0, le=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

# Prefer model_config over Config class (Pydantic v2)
class User(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    id: str
    email: str
    created_at: datetime
```

### Explicit None Handling

```python
# Bad: truthy check loses empty string/zero
def get_value(data: dict[str, Any]) -> str:
    return data.get("key") or "default"  # "" becomes "default"

# Good: explicit None check
def get_value(data: dict[str, Any]) -> str:
    value = data.get("key")
    return value if value is not None else "default"
```

### Result Types (Avoid Exceptions for Expected Cases)

```python
from typing import TypeVar, Generic

T = TypeVar("T")
E = TypeVar("E")

class Result(Generic[T, E]):
    """Explicit success/failure container."""

    def __init__(self, value: T | None = None, error: E | None = None):
        self._value = value
        self._error = error

    @property
    def is_ok(self) -> bool:
        return self._error is None

    def unwrap(self) -> T:
        if self._error is not None:
            raise ValueError(f"Unwrap on error: {self._error}")
        return self._value  # type: ignore

# Usage
def parse_int(s: str) -> Result[int, str]:
    try:
        return Result(value=int(s))
    except ValueError:
        return Result(error=f"Cannot parse '{s}' as integer")
```

### Dataclasses vs Pydantic

```python
from dataclasses import dataclass, field
from pydantic import BaseModel

# Use dataclass for internal data structures (faster, simpler)
@dataclass
class Point:
    x: float
    y: float

# Use Pydantic for external data (APIs, config, validation)
class APIResponse(BaseModel):
    data: dict[str, Any]
    status: int
```

---

## FastAPI

### Router Organization

```python
# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_db, get_current_user
from app.schemas.users import UserCreate, UserResponse
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(db)
    return await service.create(data)

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return current_user
```

### Dependency Injection

```python
from typing import Annotated
from fastapi import Depends

# Define reusable dependencies with Annotated
async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# Clean function signatures
@router.get("/items")
async def list_items(db: DBSession, user: CurrentUser) -> list[Item]:
    return await ItemService(db).list_for_user(user.id)
```

### Error Handling

```python
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request

# Custom exception class
class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code

# Exception handler
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )

# Usage in service
class NotFoundError(AppError):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", "NOT_FOUND", 404)

def get_user(user_id: str) -> User:
    user = db.get(user_id)
    if not user:
        raise NotFoundError("User")
    return user
```

### Request/Response Schemas

```python
from pydantic import BaseModel, Field
from datetime import datetime

# Separate schemas for create, update, and response
class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None

class UserResponse(UserBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}  # Replaces orm_mode
```

---

## Logging with structlog

```python
import structlog
from structlog.stdlib import BoundLogger

# Configure once at startup
def configure_logging(json_output: bool = True) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

# Usage
logger: BoundLogger = structlog.get_logger()

async def create_user(data: UserCreate) -> User:
    logger.info("creating user", email=data.email)

    try:
        user = await db.create(data)
        logger.info("user created", user_id=user.id)
        return user
    except Exception as e:
        logger.error("user creation failed", email=data.email, error=str(e))
        raise

# Request context
from structlog.contextvars import bind_contextvars

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    bind_contextvars(request_id=request_id, path=request.url.path)
    return await call_next(request)
```

---

## Testing with pytest

### Test Structure

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def user_data() -> dict[str, str]:
    return {"email": "test@example.com", "name": "Test User"}

class TestUserCreation:
    async def test_create_user_success(
        self, client: AsyncClient, user_data: dict[str, str]
    ) -> None:
        response = await client.post("/users", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data

    async def test_create_user_invalid_email(
        self, client: AsyncClient
    ) -> None:
        response = await client.post("/users", json={"email": "invalid", "name": "Test"})

        assert response.status_code == 422
```

### Fixtures

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional database session that rolls back after each test."""
    async with engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn) as session:
            yield session
        await conn.rollback()
```

### Parametrized Tests

```python
@pytest.mark.parametrize(
    "email,expected_valid",
    [
        ("user@example.com", True),
        ("user@sub.example.com", True),
        ("invalid", False),
        ("", False),
        ("user@", False),
    ],
)
def test_email_validation(email: str, expected_valid: bool) -> None:
    result = validate_email(email)
    assert result == expected_valid
```

---

## Async Patterns

### Concurrent Operations

```python
import asyncio
from typing import Sequence

async def fetch_all_users(user_ids: Sequence[str]) -> list[User]:
    """Fetch users concurrently with bounded concurrency."""
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

    async def fetch_one(user_id: str) -> User | None:
        async with semaphore:
            return await user_service.get(user_id)

    results = await asyncio.gather(
        *[fetch_one(uid) for uid in user_ids],
        return_exceptions=True,
    )

    return [r for r in results if isinstance(r, User)]
```

### Context Managers

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Provide atomic transaction with automatic rollback on failure."""
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

---

## File Organization

### Project Structure

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app creation
│   ├── config.py            # Settings with pydantic-settings
│   ├── dependencies.py      # Shared dependencies
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py
│   └── db/
│       ├── __init__.py
│       └── session.py
└── tests/
    ├── conftest.py
    ├── test_users.py
    └── test_items.py
```

### Import Order

```python
# 1. Standard library
import asyncio
import logging
from datetime import datetime
from typing import Any

# 2. Third-party
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application
from app.config import settings
from app.db import get_session
from app.services.users import UserService
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService`, `CreateUserRequest` |
| Functions | snake_case | `get_user_by_id`, `validate_email` |
| Constants | SCREAMING_SNAKE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Type variables | Single capital or PascalCase | `T`, `KeyType` |
| Private | leading underscore | `_internal_helper` |

---

## Tools

### Ruff (Linting + Formatting)

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Pyright (Type Checking)

```toml
# pyproject.toml
[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"
reportMissingImports = true
reportMissingTypeStubs = false
```

---

## Anti-Patterns

### Avoid

```python
# Bad: mutable default arguments
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items

# Good: use None and create new list
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items

# Bad: bare except
try:
    risky_operation()
except:
    pass

# Good: specific exceptions
try:
    risky_operation()
except ValueError as e:
    logger.warning("Invalid value", error=str(e))
except Exception as e:
    logger.error("Unexpected error", error=str(e))
    raise

# Bad: string formatting in logs
logger.info(f"User {user_id} logged in")  # Always evaluated

# Good: structured logging
logger.info("user logged in", user_id=user_id)  # Lazy evaluation
```

---

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
