"""Credential inventory and Keychain enrollment without secret material in Python."""

from __future__ import annotations

import json
import os
import shlex
import stat
import tomllib
from datetime import date
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, ValidationError

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.credential.models import CredentialRecord, CredentialSpec, CredentialStatus

_CONFIG_RELATIVE = Path(".config/dotfiles/credentials.toml")
_PI_AUTH_RELATIVE = Path(".pi/agent/auth.json")

_STARTER_INVENTORY = """# Machine-local credential metadata. Never put secret values in this file.
# One record is one revocable grant for one consumer boundary.
version = 1

[[credential]]
id = "google-pi"
label = "Google Gemini API for Pi"
provider = "google"
kind = "api-key"
backend = "keychain"
service = "dotfiles.credential.pi.google"
account = "api-key"
environment = "GEMINI_API_KEY"
consumers = ["Pi interactive"]
scopes = ["Gemini API"]
rotation = "manual"
required = false
pi_provider = "google"
restore = "Create a dedicated key in Google AI Studio, then run: dotfiles credential set google-pi"

[[credential]]
id = "anthropic-pi"
label = "Anthropic API for Pi"
provider = "anthropic"
kind = "api-key"
backend = "keychain"
service = "dotfiles.credential.pi.anthropic"
account = "api-key"
environment = "ANTHROPIC_API_KEY"
consumers = ["Pi interactive"]
scopes = ["Messages API"]
rotation = "manual"
required = false
pi_provider = "anthropic"
restore = "Create a dedicated Anthropic key, then run: dotfiles credential set anthropic-pi"

[[credential]]
id = "openai-pi"
label = "OpenAI API for Pi"
provider = "openai"
kind = "api-key"
backend = "keychain"
service = "dotfiles.credential.pi.openai"
account = "api-key"
environment = "OPENAI_API_KEY"
consumers = ["Pi interactive"]
scopes = ["OpenAI API"]
rotation = "manual"
required = false
pi_provider = "openai"
restore = "Create a dedicated OpenAI project key, then run: dotfiles credential set openai-pi"

[[credential]]
id = "openrouter-pi"
label = "OpenRouter API for Pi"
provider = "openrouter"
kind = "api-key"
backend = "keychain"
service = "dotfiles.credential.pi.openrouter"
account = "api-key"
environment = "OPENROUTER_API_KEY"
consumers = ["Pi interactive"]
scopes = ["OpenRouter API"]
rotation = "manual"
required = false
pi_provider = "openrouter"
restore = "Create a dedicated OpenRouter key, then run: dotfiles credential set openrouter-pi"
"""


class CredentialInventoryError(RuntimeError):
    """The local inventory or requested credential is invalid."""


def _persistent_environment() -> dict[str, str]:
    secret_suffixes = ("_API_KEY", "_AUTH_TOKEN", "_OAUTH_TOKEN")
    secret_names = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.endswith(secret_suffixes) and key not in secret_names
    }


def _pi_auth_detail(output: str) -> str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return "OAuth/API key managed by Pi"
    if isinstance(payload, dict):
        auth = cast(dict[str, object], payload).get("authType")
        if isinstance(auth, str):
            return f"Pi {auth}"
    return "OAuth/API key managed by Pi"


class _Inventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int
    credential: tuple[CredentialSpec, ...]


def inventory_path(home: Path) -> Path:
    return home / _CONFIG_RELATIVE


def initialize_inventory(home: Path) -> Path:
    """Create the metadata-only starter inventory without replacing an existing file."""
    path = inventory_path(home)
    if path.exists():
        raise CredentialInventoryError(f"inventory already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_STARTER_INVENTORY, encoding="utf-8")
    path.chmod(0o600)
    return path


class CredentialService:
    """Loads grants, checks bounded presence, and delegates entry to Keychain."""

    def __init__(self, *, runner: ProcessRunner, home: Path) -> None:
        self._runner = runner
        self._home = home

    def specs(self) -> tuple[CredentialSpec, ...]:
        path = inventory_path(self._home)
        if not path.exists():
            raise CredentialInventoryError(
                "credential inventory not initialized; run: dotfiles credential init"
            )
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode != 0o600:
            raise CredentialInventoryError(
                f"credential inventory must have mode 0600, found {mode:04o}"
            )
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            inventory = _Inventory.model_validate(raw)
        except (tomllib.TOMLDecodeError, ValidationError) as exc:
            raise CredentialInventoryError(f"invalid credential inventory: {exc}") from exc
        if inventory.version != 1:
            raise CredentialInventoryError(
                f"unsupported credential inventory version: {inventory.version}"
            )
        ids = [spec.id for spec in inventory.credential]
        if len(ids) != len(set(ids)):
            raise CredentialInventoryError("credential ids must be unique")
        return inventory.credential

    def get(self, credential_id: str) -> CredentialSpec:
        try:
            return next(spec for spec in self.specs() if spec.id == credential_id)
        except StopIteration as exc:
            raise CredentialInventoryError(f"unknown credential: {credential_id}") from exc

    def list(self) -> list[CredentialRecord]:
        return [self._check(spec) for spec in self.specs()]

    def _check(self, spec: CredentialSpec) -> CredentialRecord:
        if spec.disposition != "active":
            return CredentialRecord(
                spec=spec,
                status=cast(CredentialStatus, spec.disposition),
                detail=spec.note or "",
            )
        if spec.expires_on is not None and spec.expires_on < date.today():
            return CredentialRecord(spec=spec, status="expired", detail=str(spec.expires_on))
        if spec.backend == "file":
            return self._check_file(spec)
        if spec.backend == "pi":
            return self._check_pi(spec)
        return self._check_keychain(spec)

    def _check_file(self, spec: CredentialSpec) -> CredentialRecord:
        assert spec.path is not None
        path = (
            self._home / spec.path.removeprefix("~/")
            if spec.path.startswith("~/")
            else Path(spec.path)
        )
        if not path.exists():
            return CredentialRecord(spec=spec, status="missing", detail=str(path))
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            return CredentialRecord(
                spec=spec, status="inaccessible", detail=f"unsafe mode {mode:04o}"
            )
        return CredentialRecord(spec=spec, status="stored", detail=str(path))

    def _check_pi(self, spec: CredentialSpec) -> CredentialRecord:
        executable = self._home / ".npm-global" / "bin" / "pi"
        if not executable.is_file():
            return CredentialRecord(spec=spec, status="inaccessible", detail="Pi unavailable")
        assert spec.pi_provider is not None
        result = self._runner.run(
            (
                str(executable),
                "auth",
                "check",
                "--provider",
                spec.pi_provider,
                "--json",
                "--no-refresh",
            ),
            env=_persistent_environment(),
        )
        if result.ok and '"status":"ready"' in result.stdout.replace(" ", ""):
            return CredentialRecord(
                spec=spec, status="stored", detail=_pi_auth_detail(result.stdout)
            )
        return CredentialRecord(spec=spec, status="missing", detail="Pi auth store")

    def _check_keychain(self, spec: CredentialSpec) -> CredentialRecord:
        result = self._runner.run(self._keychain_command(spec))
        if result.ok:
            return CredentialRecord(spec=spec, status="stored", detail="Keychain")
        if result.exit_code == 44:
            return CredentialRecord(spec=spec, status="missing", detail="Keychain")
        return CredentialRecord(spec=spec, status="inaccessible", detail="Keychain unavailable")

    @staticmethod
    def _keychain_command(spec: CredentialSpec, *, reveal: bool = False) -> tuple[str, ...]:
        assert spec.service is not None
        command = ["security", "find-generic-password", "-s", spec.service]
        if spec.account:
            command.extend(("-a", spec.account))
        if reveal:
            command.append("-w")
        return tuple(command)

    def resolve_environment(self, credential_id: str) -> tuple[str, str]:
        """Resolve one Keychain grant for injection into one child process."""
        spec = self.get(credential_id)
        if spec.backend != "keychain" or not spec.environment:
            raise CredentialInventoryError(
                f"{credential_id} has no Keychain-backed environment transport"
            )
        result = self._runner.run(self._keychain_command(spec, reveal=True))
        value = result.stdout.rstrip("\n")
        if not result.ok or not value:
            raise CredentialInventoryError(f"could not resolve {credential_id} from Keychain")
        return spec.environment, value

    def set(self, credential_id: str) -> None:
        """Ask macOS security to read the value from the terminal and write Keychain."""
        spec = self.get(credential_id)
        if spec.backend != "keychain":
            raise CredentialInventoryError(
                f"{credential_id} is owned by {spec.backend}, not Keychain"
            )
        assert spec.service is not None
        command = ["security", "add-generic-password", "-U", "-s", spec.service]
        if spec.account:
            command.extend(("-a", spec.account))
        command.append("-w")
        result = self._runner.run(tuple(command), capture_output=False)
        if not result.ok:
            raise CredentialInventoryError("Keychain enrollment failed")

    def _load_pi_auth(self, auth_path: Path) -> dict[str, object]:
        if not auth_path.exists():
            return {}
        mode = stat.S_IMODE(auth_path.stat().st_mode)
        if mode & 0o077:
            raise CredentialInventoryError(f"Pi auth store has unsafe mode {mode:04o}")
        try:
            loaded = json.loads(auth_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CredentialInventoryError(f"invalid Pi auth store: {exc}") from exc
        if not isinstance(loaded, dict):
            raise CredentialInventoryError("Pi auth store must contain a JSON object")
        return cast(dict[str, object], loaded)

    def link_pi(self, credential_id: str, *, force: bool = False) -> Path:
        """Point one Pi provider at a Keychain lookup command; never copy the value."""
        spec = self.get(credential_id)
        if spec.backend != "keychain" or not spec.pi_provider:
            raise CredentialInventoryError(
                f"{credential_id} is not a Keychain-backed Pi credential"
            )
        if self._check_keychain(spec).status != "stored":
            raise CredentialInventoryError(f"{credential_id} is not stored in Keychain")
        auth_path = self._home / _PI_AUTH_RELATIVE
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._load_pi_auth(auth_path)
        if spec.pi_provider in payload and not force:
            raise CredentialInventoryError(
                f"Pi provider {spec.pi_provider} is already configured; pass --force to replace it"
            )
        key_command = "!" + " ".join(
            shlex.quote(part) for part in self._keychain_command(spec, reveal=True)
        )
        payload[spec.pi_provider] = {"type": "api_key", "key": key_command}
        temporary = auth_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(auth_path)
        return auth_path
