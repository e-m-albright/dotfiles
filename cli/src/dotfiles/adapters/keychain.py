"""macOS Keychain writer with private stdin transport and exact read-back."""

from __future__ import annotations

import hmac
import subprocess
from pathlib import Path


class KeychainWriteError(RuntimeError):
    """Raised when macOS Keychain enrollment fails."""


def _quote_argument(value: str) -> str:
    # security's command parser supports escaped double quotes, not POSIX
    # adjacent quote concatenation (so shlex.join is not appropriate here).
    if any(character in value for character in "\r\n\0"):
        raise KeychainWriteError("Keychain metadata cannot contain control characters")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class MacOSKeychainStore:
    """Never put secret bytes in process arguments, files, or diagnostic output."""

    def __init__(self, executable: Path = Path("/usr/bin/security")) -> None:
        self._executable = executable

    def set_api_key(self, *, service: str, account: str | None, label: str, value: str) -> None:
        command = ["add-generic-password", "-U", "-D", "API key", "-l", label, "-s", service]
        lookup = [str(self._executable), "find-generic-password", "-s", service]
        if account:
            command.extend(("-a", account))
            lookup.extend(("-a", account))
        # security's hidden password prompt silently truncates at 128 bytes.
        # Its command-input mode bypasses that prompt; hex keeps secret bytes
        # out of the command grammar. Both forms remain sensitive in memory.
        command.extend(("-X", value.encode("utf-8").hex()))
        private_input = " ".join(_quote_argument(part) for part in command) + "\n"
        try:
            result = subprocess.run(
                [str(self._executable), "-i"],
                input=private_input.encode("utf-8"),
                capture_output=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                raise KeychainWriteError(
                    f"Keychain enrollment failed with status {result.returncode}"
                )
            verified = subprocess.run([*lookup, "-w"], capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise KeychainWriteError("Keychain enrollment did not complete") from None
        if verified.returncode != 0 or not hmac.compare_digest(
            verified.stdout.removesuffix(b"\n"), value.encode("utf-8")
        ):
            # Fail explicitly on any CLI size/encoding limit; use Security.framework
            # directly if future credential formats exceed this transport's limits.
            raise KeychainWriteError("Keychain read-back did not match the supplied credential")
