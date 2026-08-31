"""Typed credential inventory records. Secret values never enter these models."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CredentialKind = Literal["api-key", "oauth", "password", "client-secret", "session"]
CredentialBackend = Literal["keychain", "file", "pi"]
CredentialStatus = Literal["stored", "missing", "expired", "inaccessible", "superseded", "deferred"]
RotationPolicy = Literal["manual", "provider", "never", "unknown"]
CredentialDisposition = Literal["active", "superseded", "deferred"]


class CredentialSpec(BaseModel):
    """One application grant and its non-secret metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str
    provider: str
    kind: CredentialKind
    backend: CredentialBackend
    service: str | None = None
    account: str | None = None
    path: str | None = None
    environment: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")
    consumers: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    expires_on: date | None = None
    rotation: RotationPolicy = "unknown"
    disposition: CredentialDisposition = "active"
    required: bool = False
    pi_provider: str | None = None
    restore: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_backend(self) -> CredentialSpec:
        if self.backend == "keychain" and not self.service:
            raise ValueError("keychain credentials require service")
        if self.backend == "file" and not self.path:
            raise ValueError("file credentials require path")
        if self.backend == "pi" and not self.pi_provider:
            raise ValueError("Pi credentials require pi_provider")
        if self.pi_provider and self.backend not in {"keychain", "pi"}:
            raise ValueError("pi_provider requires a keychain or Pi backend")
        return self


class CredentialRecord(BaseModel):
    """Inventory metadata plus a bounded local presence result."""

    model_config = ConfigDict(frozen=True)

    spec: CredentialSpec
    status: CredentialStatus
    detail: str = ""
