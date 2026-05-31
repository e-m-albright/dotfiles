#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/macos/remote-setup.sh"

pass() { printf "✓ %s\n" "$1"; }
fail() { printf "✗ %s\n" "$1" >&2; exit 1; }
assert_contains() {
    local haystack="$1"
    local needle="$2"
    if [[ "$haystack" != *"$needle"* ]]; then
        printf "Expected output to contain: %s\n" "$needle" >&2
        printf "Actual output:\n%s\n" "$haystack" >&2
        exit 1
    fi
}
assert_file_contains_once() {
    local file="$1"
    local needle="$2"
    local count
    count=$(grep -Fxc "$needle" "$file" || true)
    [[ "$count" == "1" ]] || fail "expected exactly one authorized_keys entry, got $count"
}

setup_fake_path() {
    local bin_dir="$1"
    mkdir -p "$bin_dir"
    cat > "$bin_dir/brew" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "list" ]]; then exit 0; fi
if [[ "$1" == "install" ]]; then exit 0; fi
exit 0
STUB
    cat > "$bin_dir/systemsetup" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "-getremotelogin" ]]; then echo "Remote Login: Off"; exit 0; fi
exit 0
STUB
    cat > "$bin_dir/tailscale" <<'STUB'
#!/usr/bin/env bash
case "$1" in
    status) exit 0 ;;
    ip) echo "fake-tailnet-ip" ;;
    *) exit 0 ;;
esac
STUB
    cat > "$bin_dir/scutil" <<'STUB'
#!/usr/bin/env bash
echo "my-macbook"
STUB
    cat > "$bin_dir/sudo" <<'STUB'
#!/usr/bin/env bash
"$@"
STUB
    chmod +x "$bin_dir"/*
}

test_dry_run_prints_actions_without_mutating_home() {
    local tmp home bin output
    tmp=$(mktemp -d)
    home="$tmp/home"
    bin="$tmp/bin"
    mkdir -p "$home"
    setup_fake_path "$bin"

    output=$(HOME="$home" PATH="$bin:$PATH" "$SCRIPT" --dry-run 2>&1)

    assert_contains "$output" "Packages"
    assert_contains "$output" "DRY RUN: sudo systemsetup -setremotelogin on"
    assert_contains "$output" "mosh --server=/opt/homebrew/bin/mosh-server"
    [[ ! -e "$home/.ssh" ]] || fail "dry run should not create ~/.ssh"
    pass "dry run prints setup actions without mutating HOME"
}

test_add_key_is_idempotent() {
    local tmp home bin key output
    tmp=$(mktemp -d)
    home="$tmp/home"
    bin="$tmp/bin"
    key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeTermiusKey termius-phone"
    mkdir -p "$home"
    setup_fake_path "$bin"

    HOME="$home" PATH="$bin:$PATH" "$SCRIPT" --add-key "$key" >/dev/null
    output=$(HOME="$home" PATH="$bin:$PATH" "$SCRIPT" --add-key "$key" 2>&1)

    assert_contains "$output" "Phone public key already present"
    assert_file_contains_once "$home/.ssh/authorized_keys" "$key"
    pass "--add-key appends the Termius key only once"
}

test_dry_run_prints_actions_without_mutating_home
test_add_key_is_idempotent
