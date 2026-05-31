#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/macos/remote-disable.sh"

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

setup_fake_path() {
    local bin_dir="$1"
    mkdir -p "$bin_dir"
    cat > "$bin_dir/systemsetup" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "-getremotelogin" ]]; then echo "Remote Login: On"; exit 0; fi
exit 0
STUB
    cat > "$bin_dir/sudo" <<'STUB'
#!/usr/bin/env bash
"$@"
STUB
    chmod +x "$bin_dir"/*
}

test_dry_run_prints_disable_action() {
    local tmp bin output
    tmp=$(mktemp -d)
    bin="$tmp/bin"
    setup_fake_path "$bin"

    output=$(PATH="$bin:$PATH" "$SCRIPT" --dry-run 2>&1)

    assert_contains "$output" "DRY RUN: sudo systemsetup -setremotelogin off"
    assert_contains "$output" "Remote Login will be disabled"
    pass "dry run prints Remote Login disable action"
}

test_dry_run_prints_session_kill_actions() {
    local tmp bin output
    tmp=$(mktemp -d)
    bin="$tmp/bin"
    setup_fake_path "$bin"

    output=$(PATH="$bin:$PATH" "$SCRIPT" --dry-run --kill-sessions 2>&1)

    assert_contains "$output" "DRY RUN: pkill -u"
    assert_contains "$output" "mosh-server"
    assert_contains "$output" "DRY RUN: pkill -u"
    assert_contains "$output" "sshd"
    pass "dry run prints session kill actions"
}

test_dry_run_prints_disable_action
test_dry_run_prints_session_kill_actions
