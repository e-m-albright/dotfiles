"""Credential inventory and Keychain enrollment without secret material in Python."""

from __future__ import annotations

import json
import os
import shlex
import stat
import tomllib
from datetime import date
from pathlib import Path
from tempfile import mkstemp
from typing import cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, ValidationError

from dotfiles.adapters.keychain import KeychainWriteError
from dotfiles.adapters.ports import KeychainStore, ProcessRunner
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


def _persistent_environment(home: Path) -> dict[str, str]:
    """Inspect persisted auth without ambient grants or runtime injection settings."""
    allowed = {"HOME", "PATH", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE"}
    return {
        **{key: value for key, value in os.environ.items() if key in allowed},
        "HOME": str(home),
    }


def _pi_auth_detail(output: str) -> str | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    data = cast(dict[str, object], payload)
    if data.get("status") != "ready":
        return None
    auth = data.get("authType")
    return f"Pi {auth}" if isinstance(auth, str) else "OAuth/API key managed by Pi"


def _write_private(path: Path, text: str, *, replace: bool = True) -> None:
    """Publish complete text atomically; temporary content is private from creation."""
    descriptor, name = mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        if replace:
            temporary.replace(path)
        else:
            # Exclusive publication never overwrites an existing inventory.
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class _Inventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int
    credential: tuple[CredentialSpec, ...]


def inventory_path(home: Path) -> Path:
    return home / _CONFIG_RELATIVE


def initialize_inventory(home: Path) -> Path:
    """Create the metadata-only starter inventory without replacing an existing file."""
    path = inventory_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_private(path, _STARTER_INVENTORY, replace=False)
    except FileExistsError as exc:
        raise CredentialInventoryError(f"inventory already exists: {path}") from exc
    return path


def _credential_block(text: str, credential_id: str) -> tuple[int, int, list[str]]:
    marker = f'id = "{credential_id}"'
    identifier = text.find(marker)
    if identifier < 0:
        raise CredentialInventoryError(f"unknown credential: {credential_id}")
    start = text.rfind("[[credential]]", 0, identifier)
    following = text.find("[[credential]]", identifier)
    end = len(text) if following < 0 else following
    return start, end, text[start:end].splitlines(keepends=True)


def _line_indexes(lines: list[str], prefix: str) -> list[int]:
    return [index for index, line in enumerate(lines) if line.startswith(prefix)]


def _replace_endpoint(text: str, credential_id: str, endpoint: str) -> str:
    start, end, lines = _credential_block(text, credential_id)
    matches = _line_indexes(lines, "endpoint = ")
    if len(matches) > 1:
        raise CredentialInventoryError(f"{credential_id} has duplicate endpoint metadata")
    replacement = f"endpoint = {json.dumps(endpoint)}\n"
    if matches:
        lines[matches[0]] = replacement
    else:
        environments = _line_indexes(lines, "endpoint_environment = ")
        if len(environments) != 1:
            raise CredentialInventoryError(f"{credential_id} does not declare endpoint metadata")
        lines.insert(environments[0], replacement)
    return text[:start] + "".join(lines) + text[end:]


class CredentialService:
    """Loads grants, checks bounded presence, and delegates entry to Keychain."""

    def __init__(
        self, *, runner: ProcessRunner, home: Path, keychain: KeychainStore | None = None
    ) -> None:
        self._runner = runner
        self._keychain = keychain
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
            env=_persistent_environment(self._home),
            timeout=10,
        )
        detail = _pi_auth_detail(result.stdout) if result.ok else None
        if detail is not None:
            return CredentialRecord(spec=spec, status="stored", detail=detail)
        return CredentialRecord(spec=spec, status="missing", detail="Pi auth store")

    def _check_keychain(self, spec: CredentialSpec) -> CredentialRecord:
        result = self._runner.run(self._keychain_command(spec), timeout=10)
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

    def resolve_environment_bundle(self, credential_id: str) -> dict[str, str]:
        """Resolve a secret and its declared non-secret endpoint for one child."""
        name, value = self.resolve_environment(credential_id)
        spec = self.get(credential_id)
        environment = {name: value}
        if spec.endpoint_environment and spec.endpoint:
            environment[spec.endpoint_environment] = spec.endpoint
        return environment

    @staticmethod
    def validate_endpoint(value: str) -> str:
        endpoint = value.strip()
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise CredentialInventoryError(
                "endpoint must be an HTTP(S) URL without embedded credentials"
            )
        return endpoint

    def set_endpoint(self, credential_id: str, value: str) -> None:
        """Save one non-secret endpoint beside its private inventory declaration."""
        spec = self.get(credential_id)
        if not spec.endpoint_environment:
            raise CredentialInventoryError(f"{credential_id} does not declare endpoint metadata")
        endpoint = self.validate_endpoint(value)
        path = inventory_path(self._home)
        text = path.read_text(encoding="utf-8")
        updated = _replace_endpoint(text, credential_id, endpoint)
        _write_private(path, updated)

    def set(self, credential_id: str, value: str) -> None:
        """Pipe one supplied secret to macOS Keychain without exposing it in argv."""
        spec = self.get(credential_id)
        if spec.backend != "keychain":
            raise CredentialInventoryError(
                f"{credential_id} is owned by {spec.backend}, not Keychain"
            )
        if not value:
            raise CredentialInventoryError("credential value cannot be empty")
        assert spec.service is not None
        if self._keychain is None:
            raise CredentialInventoryError("Keychain writer is unavailable")
        try:
            self._keychain.set_api_key(
                service=spec.service,
                account=spec.account,
                label=spec.label,
                value=value,
            )
        except KeychainWriteError as exc:
            raise CredentialInventoryError(str(exc)) from exc

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
        _write_private(auth_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return auth_path
