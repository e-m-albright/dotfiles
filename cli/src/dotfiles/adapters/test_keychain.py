from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dotfiles.adapters import keychain as keychain_module
from dotfiles.adapters.keychain import KeychainWriteError, MacOSKeychainStore


def _fake_security(tmp_path: Path, *, mode: str = "normal") -> Path:
    path = tmp_path / "security"
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, shlex, sys\n"
        f"root = pathlib.Path({str(tmp_path)!r})\n"
        f"mode = {mode!r}\n"
        "with (root / 'argv.jsonl').open('a') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:] == ['-i']:\n"
        "    command = shlex.split(sys.stdin.readline())\n"
        "    if mode == 'error': sys.exit(2)\n"
        "    value = bytes.fromhex(command[command.index('-X') + 1])\n"
        "    (root / 'value').write_bytes(value[:128] if mode == 'truncate' else value)\n"
        "elif sys.argv[1] == 'add-generic-password':\n"
        # Reproduce security's hidden prompt limit, not an unlimited shell read.
        "    print('password data for new item: ', end='', flush=True)\n"
        "    value = sys.stdin.readline().rstrip('\\n').encode()[:128]\n"
        "    print('retype password for new item: ', end='', flush=True)\n"
        "    sys.stdin.readline()\n"
        "    (root / 'value').write_bytes(value)\n"
        "else:\n"
        "    if mode == 'read-error': sys.exit(44)\n"
        "    sys.stdout.buffer.write((root / 'value').read_bytes() + b'\\n')\n"
    )
    path.chmod(0o700)
    return path


@pytest.mark.parametrize("value", ["short-test", "synthetic-test-" + "A1b2C3d4" * 40])
def test_keychain_writer_preserves_full_value_without_secret_arguments(
    tmp_path: Path, value: str
) -> None:
    executable = _fake_security(tmp_path)
    MacOSKeychainStore(executable).set_api_key(
        service="example.service", account="api-key", label='Owner\'s "API key"', value=value
    )
    assert (tmp_path / "value").read_bytes() == value.encode()
    arguments = (tmp_path / "argv.jsonl").read_text()
    assert value not in arguments
    assert value.encode().hex() not in arguments
    assert json.loads(arguments.splitlines()[-1])[0] == "find-generic-password"


@pytest.mark.parametrize("mode", ["error", "read-error", "truncate"])
def test_keychain_writer_fails_closed_on_write_or_readback_failure(
    tmp_path: Path, mode: str
) -> None:
    value = "synthetic-test-" + "A1b2C3d4" * 40
    with pytest.raises(KeychainWriteError) as error:
        MacOSKeychainStore(_fake_security(tmp_path, mode=mode)).set_api_key(
            service="example.service", account=None, label="Example", value=value
        )
    assert value not in str(error.value)
    assert value.encode().hex() not in str(error.value)


def test_keychain_writer_bounds_execution_without_leaking_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("security", 30, output="synthetic-test")

    monkeypatch.setattr(keychain_module.subprocess, "run", timeout)
    with pytest.raises(KeychainWriteError, match="did not complete") as error:
        MacOSKeychainStore().set_api_key(
            service="example", account=None, label="Example", value="synthetic-test"
        )
    assert "synthetic-test" not in str(error.value)


@pytest.mark.parametrize("metadata", ["bad\nlabel", "bad\rlabel", "bad\0label"])
def test_keychain_writer_rejects_command_boundaries_before_mutation(
    tmp_path: Path, metadata: str
) -> None:
    with pytest.raises(KeychainWriteError, match="control characters"):
        MacOSKeychainStore(_fake_security(tmp_path)).set_api_key(
            service="example", account=None, label=metadata, value="synthetic-test"
        )
    assert not (tmp_path / "argv.jsonl").exists()
