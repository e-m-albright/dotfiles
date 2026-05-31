"""Remote-shell setup/disable logic. Pure decisions over the ProcessRunner/FileSystem ports."""

_KEY_PREFIXES = ("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")


def is_ssh_public_key(value: str) -> bool:
    """True if value looks like an SSH public key line (prefix + a key body)."""
    if not value.startswith(_KEY_PREFIXES):
        return False
    parts = value.split()
    return len(parts) >= 2 and bool(parts[1])
