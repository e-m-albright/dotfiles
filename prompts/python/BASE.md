# AGENTS.md — Python (Base)

Cross-platform instructions for AI coding agents.
Works with: Claude Code, Cursor, Windsurf, Gemini, ChatGPT, GitHub Copilot.

---

## Quick Reference

```yaml
Runtime:     Python 3.12+ (via UV)
Validation:  Pydantic v2
Logging:     structlog + Rich
Testing:     pytest + pytest-asyncio + Hypothesis
Linting:     Ruff (lint + format)
Types:       Pyright
Tasks:       Just
Debugging:   icecream + ipdb
```

---

## Commands (Shared)

```bash
# Environment
uv sync                    # Install dependencies
uv run python app.py       # Run with project environment
uv add package             # Add dependency
uv add --dev package       # Add dev dependency

# Quality
just check                 # Run all checks (lint, type, test)
just lint                  # Ruff lint
just format                # Ruff format
just typecheck             # Pyright type check

# Testing
just test                  # Run tests
just test-cov              # Run tests with coverage
just test-watch            # Run tests in watch mode
```

---

## Pydantic Schema

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with shared fields."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)."""

    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
```

---

## Configuration (Pydantic Settings)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    debug: bool = False
    app_name: str = "My API"

    # Database
    database_url: str

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 30


settings = Settings()
```

---

## Logging (structlog + Rich)

```python
import logging
import structlog

def setup_logging(debug: bool = False) -> None:
    """Configure structlog with Rich for beautiful console output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
log = structlog.get_logger()
log.info("server_started", port=8000, env="production")
log.error("request_failed", error=str(e), request_id=req_id)
```

---

## Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st, settings
import pytest

# Basic property test
@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs: list[int]) -> None:
    """Sorting twice gives same result as sorting once."""
    assert sorted(sorted(xs)) == sorted(xs)


# Test with custom strategies
@given(
    email=st.emails(),
    name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))),
)
def test_user_create_schema_validates(email: str, name: str) -> None:
    """UserCreate schema accepts valid inputs."""
    from app.schemas.user import UserCreate
    user = UserCreate(email=email, name=name, password="validpassword123")
    assert user.email == email


# Async property test
@pytest.mark.asyncio
@given(user_id=st.integers(min_value=1))
@settings(max_examples=50)  # Limit examples for async tests
async def test_get_nonexistent_user_returns_none(db_session, user_id: int) -> None:
    """Getting a non-existent user returns None."""
    from app.services.user import UserService
    service = UserService(db_session)
    result = await service.get_by_id(user_id)
    assert result is None
```

---

## Debugging with icecream

```python
from icecream import ic

# Instead of print debugging
def process_order(order: Order) -> Result:
    ic(order.id, order.status)  # ic| order.id: 42, order.status: 'pending'

    total = calculate_total(order.items)
    ic(total)  # ic| total: 159.99

    if total > 100:
        ic("applying discount")  # ic| 'applying discount'
        total *= 0.9

    return Result(total=total)

# Disable in production
import os
if os.getenv("ENV") == "production":
    ic.disable()
```

---

## Type Hints

### Standard Library Types

```python
from collections.abc import Callable, Sequence, Mapping, AsyncGenerator
from typing import Any, TypeVar, Generic

# Use | for unions (Python 3.10+)
def process(value: str | None) -> str | None: ...

# Use lowercase for built-in types (Python 3.9+)
def get_items() -> list[str]: ...
def get_mapping() -> dict[str, int]: ...
```

### Generic Types

```python
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int
```

---

## Error Handling

### Custom Exceptions

```python
# app/core/errors.py

class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND")


class ValidationError(AppError):
    """Validation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")
```

---

## File Naming

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `user_service.py`, `auth_utils.py` |
| Classes | PascalCase | `class UserService:`, `class AuthToken:` |
| Functions | snake_case | `def get_user_by_id():` |
| Constants | SCREAMING_SNAKE | `MAX_RETRIES = 3`, `API_VERSION = "v1"` |
| Type Variables | PascalCase | `T = TypeVar("T")` |

---

## Git Conventions

### Commit Messages

```
type(scope): description

feat(api): add user registration endpoint
fix(db): handle connection timeout gracefully
refactor(services): extract validation logic
test(api): add user creation tests
docs(readme): update installation steps
chore(deps): bump fastapi to 0.115.0
```

---

## Agent Output Rules

1. **All artifacts go in `.agents/`** — Never create random files in project root
2. **Date-prefix plans** — `YYYY-MM-DD-feature-name.md`
3. **Update .agents/README.md** — Keep index of all agent-generated files
4. **Clean working files** — Delete when no longer needed
5. **Architecture decisions** — Go in `.architecture/adr/`, not `.agents/`

---

## Critical Rules

### Always

- Use type hints on all function signatures
- Use Pydantic models for all validation
- Run `just check` before committing

### Never

- Use `Any` type — use `Unknown` and narrow, or be specific
- Use mutable default arguments — `def f(items: list = None)` is wrong
- Import with `*` — always explicit imports
- Catch bare `Exception` — be specific

### Ask First

- Adding new dependencies
- Changing database schema
- Modifying auth flow
- Deleting files
