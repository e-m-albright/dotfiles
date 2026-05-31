from dotfiles_cli.core.remote import is_ssh_public_key


def test_accepts_ed25519_rsa_ecdsa() -> None:
    assert is_ssh_public_key("ssh-ed25519 AAAAC3Nza... phone")
    assert is_ssh_public_key("ssh-rsa AAAAB3Nza... phone")
    assert is_ssh_public_key("ecdsa-sha2-nistp256 AAAA... phone")


def test_rejects_garbage_and_private_keys() -> None:
    assert not is_ssh_public_key("hello world")
    assert not is_ssh_public_key("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert not is_ssh_public_key("")
    assert not is_ssh_public_key("ssh-ed25519")  # no key body
