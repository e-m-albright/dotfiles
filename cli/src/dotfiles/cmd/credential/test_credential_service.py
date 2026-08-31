from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from pydantic import ValidationError

from dotfiles.cmd.credential.models import CredentialSpec
from dotfiles.cmd.credential.service import (
    CredentialInventoryError,
    CredentialService,
    initialize_inventory,
)
from dotfiles.testing.fakes import FakeProcessRunner


def _inventory(home: Path) -> Path:
    path = home / ".config" / "dotfiles" / "credentials.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """version = 1

[[credential]]
id = "google-pi"
label = "Google API for Pi"
provider = "google"
kind = "api-key"
backend = "keychain"
service = "dotfiles.credential.pi.google"
account = "api-key"
environment = "GEMINI_API_KEY"
consumers = ["Pi interactive"]
scopes = ["Gemini API"]
rotation = "manual"
required = true
pi_provider = "google"

[[credential]]
id = "gmail-oauth"
label = "Gmail OAuth"
provider = "google"
kind = "oauth"
backend = "file"
path = "~/Library/Application Support/example/token.json"
consumers = ["Example"]
scopes = ["gmail.modify"]
rotation = "provider"
required = false
""",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


@pytest.mark.parametrize(
    "values",
    [
        {"backend": "keychain"},
        {"backend": "file"},
        {"backend": "pi"},
        {"backend": "file", "path": "~/token", "pi_provider": "google"},
    ],
)
def test_credential_backend_requires_its_bounded_reference(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CredentialSpec.model_validate(
            {
                "id": "example",
                "label": "Example",
                "provider": "example",
                "kind": "api-key",
                **values,
            }
        )


def test_load_requires_private_inventory_permissions(tmp_path: Path) -> None:
    path = _inventory(tmp_path)
    path.chmod(0o644)

    with pytest.raises(CredentialInventoryError, match="0600"):
        CredentialService(runner=FakeProcessRunner(), home=tmp_path).list()


def test_list_checks_keychain_metadata_without_reading_secret(tmp_path: Path) -> None:
    _inventory(tmp_path)
    runner = FakeProcessRunner()
    command = (
        "security",
        "find-generic-password",
        "-s",
        "dotfiles.credential.pi.google",
        "-a",
        "api-key",
    )
    runner.script(command, stdout='keychain: "login.keychain-db"\n')

    records = CredentialService(runner=runner, home=tmp_path).list()

    assert [record.status for record in records] == ["stored", "missing"]
    assert command in runner.calls
    assert "-w" not in command


def test_resolve_environment_reads_only_the_requested_grant(tmp_path: Path) -> None:
    _inventory(tmp_path)
    runner = FakeProcessRunner()
    command = (
        "security",
        "find-generic-password",
        "-s",
        "dotfiles.credential.pi.google",
        "-a",
        "api-key",
        "-w",
    )
    runner.script(command, stdout="test-value\n")

    name, value = CredentialService(runner=runner, home=tmp_path).resolve_environment("google-pi")

    assert name == "GEMINI_API_KEY"
    assert value == "test-value"
    assert runner.calls == [command]


def test_set_uses_interactive_security_prompt_and_never_argv_or_captured_output(
    tmp_path: Path,
) -> None:
    _inventory(tmp_path)
    runner = FakeProcessRunner()

    CredentialService(runner=runner, home=tmp_path).set("google-pi")

    command = runner.calls[-1]
    assert command == (
        "security",
        "add-generic-password",
        "-U",
        "-s",
        "dotfiles.credential.pi.google",
        "-a",
        "api-key",
        "-w",
    )
    assert runner.inputs[-1] is None
    assert runner.capture_output[-1] is False


def test_link_pi_writes_keychain_command_reference_without_secret(tmp_path: Path) -> None:
    _inventory(tmp_path)
    auth = tmp_path / ".pi" / "agent" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text(json.dumps({"openai-codex": {"type": "oauth", "access": "hidden"}}))
    auth.chmod(0o600)

    CredentialService(runner=FakeProcessRunner(), home=tmp_path).link_pi("google-pi")

    payload = json.loads(auth.read_text())
    assert payload["openai-codex"]["access"] == "hidden"
    assert payload["google"] == {
        "type": "api_key",
        "key": "!security find-generic-password -s dotfiles.credential.pi.google -a api-key -w",
    }
    assert stat.S_IMODE(auth.stat().st_mode) == 0o600


def test_link_pi_requires_stored_keychain_grant(tmp_path: Path) -> None:
    _inventory(tmp_path)
    runner = FakeProcessRunner()
    runner.script(
        (
            "security",
            "find-generic-password",
            "-s",
            "dotfiles.credential.pi.google",
            "-a",
            "api-key",
        ),
        exit_code=44,
    )

    with pytest.raises(CredentialInventoryError, match="not stored"):
        CredentialService(runner=runner, home=tmp_path).link_pi("google-pi")


def test_link_pi_refuses_to_replace_existing_provider_without_force(tmp_path: Path) -> None:
    _inventory(tmp_path)
    auth = tmp_path / ".pi" / "agent" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text(json.dumps({"google": {"type": "api_key", "key": "existing"}}))
    auth.chmod(0o600)

    with pytest.raises(CredentialInventoryError, match="already configured"):
        CredentialService(runner=FakeProcessRunner(), home=tmp_path).link_pi("google-pi")


def test_file_status_distinguishes_stored_unsafe_missing_and_expired(tmp_path: Path) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    stored = tmp_path / "stored.json"
    unsafe = tmp_path / "unsafe.json"
    stored.write_text("{}")
    unsafe.write_text("{}")
    stored.chmod(0o600)
    unsafe.chmod(0o644)
    inventory.write_text(
        f'''version = 1
[[credential]]
id = "stored"
label = "Stored"
provider = "example"
kind = "oauth"
backend = "file"
path = "{stored}"
[[credential]]
id = "unsafe"
label = "Unsafe"
provider = "example"
kind = "oauth"
backend = "file"
path = "{unsafe}"
[[credential]]
id = "missing"
label = "Missing"
provider = "example"
kind = "oauth"
backend = "file"
path = "{tmp_path / "missing.json"}"
[[credential]]
id = "expired"
label = "Expired"
provider = "example"
kind = "api-key"
backend = "keychain"
service = "expired"
expires_on = 2000-01-01
'''
    )
    inventory.chmod(0o600)

    records = CredentialService(runner=FakeProcessRunner(), home=tmp_path).list()

    assert [record.status for record in records] == [
        "stored",
        "inaccessible",
        "missing",
        "expired",
    ]


def test_pi_backend_checks_provider_without_ambient_api_keys(tmp_path: Path, monkeypatch) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        """version = 1
[[credential]]
id = "anthropic-pi"
label = "Anthropic in Pi"
provider = "anthropic"
kind = "oauth"
backend = "pi"
pi_provider = "anthropic"
"""
    )
    inventory.chmod(0o600)
    executable = tmp_path / ".npm-global" / "bin" / "pi"
    executable.parent.mkdir(parents=True)
    executable.touch()
    runner = FakeProcessRunner()
    command = (
        str(executable),
        "auth",
        "check",
        "--provider",
        "anthropic",
        "--json",
        "--no-refresh",
    )
    runner.script(command, stdout='{"status":"ready","authType":"oauth"}')
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-only")

    record = CredentialService(runner=runner, home=tmp_path).list()[0]

    assert record.status == "stored"
    assert record.detail == "Pi oauth"
    assert runner.calls == [command]


def test_pi_backend_reports_unavailable_missing_and_untyped_ready(tmp_path: Path) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        """version = 1
[[credential]]
id = "openrouter-pi"
label = "OpenRouter in Pi"
provider = "openrouter"
kind = "api-key"
backend = "pi"
pi_provider = "openrouter"
"""
    )
    inventory.chmod(0o600)
    runner = FakeProcessRunner()
    service = CredentialService(runner=runner, home=tmp_path)

    assert service.list()[0].status == "inaccessible"

    executable = tmp_path / ".npm-global" / "bin" / "pi"
    executable.parent.mkdir(parents=True)
    executable.touch()
    command = (
        str(executable),
        "auth",
        "check",
        "--provider",
        "openrouter",
        "--json",
        "--no-refresh",
    )
    runner.script(command, exit_code=1, stdout='{"status":"not_ready"}')
    assert service.list()[0].status == "missing"

    runner.script(command, stdout='{"status":"ready"} trailing')
    record = service.list()[0]
    assert record.status == "stored"
    assert record.detail == "OAuth/API key managed by Pi"


def test_superseded_grant_is_resolved_without_checking_backend(tmp_path: Path) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        """version = 1
[[credential]]
id = "openai-pi"
label = "Raw OpenAI"
provider = "openai"
kind = "api-key"
backend = "keychain"
service = "unused"
disposition = "superseded"
note = "Covered by OpenAI Codex OAuth"
"""
    )
    inventory.chmod(0o600)
    runner = FakeProcessRunner()

    record = CredentialService(runner=runner, home=tmp_path).list()[0]

    assert record.status == "superseded"
    assert record.detail == "Covered by OpenAI Codex OAuth"
    assert runner.calls == []


def test_deferred_grant_is_resolved_without_checking_backend(tmp_path: Path) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        """version = 1
[[credential]]
id = "anthropic-pi"
label = "Anthropic"
provider = "anthropic"
kind = "oauth"
backend = "pi"
pi_provider = "anthropic"
disposition = "deferred"
note = "Paid access unavailable"
"""
    )
    inventory.chmod(0o600)

    record = CredentialService(runner=FakeProcessRunner(), home=tmp_path).list()[0]

    assert record.status == "deferred"
    assert record.detail == "Paid access unavailable"


def test_file_backend_expands_tilde_from_injected_home(tmp_path: Path) -> None:
    inventory = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    inventory.parent.mkdir(parents=True)
    token = tmp_path / "private" / "token.json"
    token.parent.mkdir()
    token.write_text("{}")
    token.chmod(0o600)
    inventory.write_text(
        """version = 1
[[credential]]
id = "token"
label = "Token"
provider = "example"
kind = "oauth"
backend = "file"
path = "~/private/token.json"
"""
    )
    inventory.chmod(0o600)

    record = CredentialService(runner=FakeProcessRunner(), home=tmp_path).list()[0]

    assert record.status == "stored"
    assert record.detail == str(token)


def test_keychain_status_distinguishes_missing_and_inaccessible(tmp_path: Path) -> None:
    _inventory(tmp_path)
    runner = FakeProcessRunner()
    command = (
        "security",
        "find-generic-password",
        "-s",
        "dotfiles.credential.pi.google",
        "-a",
        "api-key",
    )
    runner.script(command, exit_code=44)
    records = CredentialService(runner=runner, home=tmp_path).list()
    assert records[0].status == "missing"

    runner.script(command, exit_code=1)
    records = CredentialService(runner=runner, home=tmp_path).list()
    assert records[0].status == "inaccessible"


def test_invalid_inventory_shapes_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".config" / "dotfiles" / "credentials.toml"
    path.parent.mkdir(parents=True)
    path.write_text("version = 2\ncredential = []\n")
    path.chmod(0o600)
    service = CredentialService(runner=FakeProcessRunner(), home=tmp_path)
    with pytest.raises(CredentialInventoryError, match="unsupported"):
        service.specs()

    path.write_text("version = 1\ncredential = [")
    with pytest.raises(CredentialInventoryError, match="invalid"):
        service.specs()

    path.write_text(
        """version = 1
[[credential]]
id = "same"
label = "One"
provider = "x"
kind = "oauth"
backend = "file"
path = "~/one"
[[credential]]
id = "same"
label = "Two"
provider = "x"
kind = "oauth"
backend = "file"
path = "~/two"
"""
    )
    with pytest.raises(CredentialInventoryError, match="unique"):
        service.specs()


def test_invalid_operations_fail_closed(tmp_path: Path) -> None:
    _inventory(tmp_path)
    service = CredentialService(runner=FakeProcessRunner(), home=tmp_path)
    with pytest.raises(CredentialInventoryError, match="unknown"):
        service.get("unknown")
    with pytest.raises(CredentialInventoryError, match="owned by file"):
        service.set("gmail-oauth")
    with pytest.raises(CredentialInventoryError, match="no Keychain-backed"):
        service.resolve_environment("gmail-oauth")
    with pytest.raises(CredentialInventoryError, match="not a Keychain-backed Pi"):
        service.link_pi("gmail-oauth")


def test_initialize_creates_metadata_only_inventory_with_private_mode(tmp_path: Path) -> None:
    path = initialize_inventory(tmp_path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    text = path.read_text()
    assert "google-pi" in text
    assert "anthropic-pi" in text
    assert "openai-pi" in text
    assert "openrouter-pi" in text
    assert "api_key" not in text
