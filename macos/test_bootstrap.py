"""Exercise installer orchestration with an isolated home and explicit command stubs."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


class ShellSandbox:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / "home"
        self.bin = root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.log = root / "commands"
        self.log.touch()
        # Never inherit the host PATH, credentials, shell hooks, or agent sockets.
        self.env = {
            "HOME": str(self.home),
            "PATH": str(self.bin),
            "SHELL": str(self.bin / "zsh"),
            "USER": "test",
            "COMMAND_LOG": str(self.log),
            "TMPDIR": str(root),
        }

    def allow(self, *commands: str) -> None:
        for command in commands:
            executable = shutil.which(command)
            assert executable, command
            (self.bin / command).symlink_to(executable)

    def stub(self, name: str, body: str = "exit 0") -> Path:
        script = self.bin / name
        script.write_text(
            '#!/bin/bash\nset -eu\nprintf "%s %s\\n" "${0##*/}" "$*" '
            '>> "$COMMAND_LOG"\n' + body + "\n"
        )
        script.chmod(0o755)
        return script

    def run(self, script: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "/bin/bash",
                "-c",
                'OSTYPE=darwin; script="$1"; shift; source "$script"',
                "test",
                str(script),
            ],
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )


@pytest.fixture
def installer(tmp_path: Path) -> tuple[ShellSandbox, Path]:
    sandbox = ShellSandbox(tmp_path)
    sandbox.allow("dirname", "mkdir", "head", "grep", "cat")
    sandbox.stub("which", 'command -v "$1"')
    sandbox.stub("zsh")
    sandbox.stub("brew", '[[ "${1:-}" == --version ]] && echo "Homebrew test"; exit 0')
    sandbox.stub("uv", '[[ "$*" != "${FAIL_STEP:-}" ]]')
    sandbox.stub("python3.14")
    sandbox.stub("curl", "exit 22")
    sandbox.stub("sh", "exit 1")
    repo = tmp_path / "repo"
    (repo / "macos").mkdir(parents=True)
    (repo / "bin").mkdir()
    script = repo / "install.sh"
    shutil.copyfile(ROOT / "install.sh", script)
    shutil.copyfile(ROOT / "macos/print_utils.sh", repo / "macos/print_utils.sh")
    # Link mechanics have their own tests; this also blocks /opt/homebrew writes.
    (repo / "macos/link_utils.sh").write_text("safe_link() { :; }\n")
    for name in ("ssh.sh", "dock.sh", "file-associations.sh", "login-items.sh", "orbstack.sh"):
        (repo / "macos" / name).symlink_to(sandbox.stub(name))
    (repo / "bin/dotfiles").symlink_to(sandbox.stub("dotfiles"))
    (sandbox.home / ".oh-my-zsh").mkdir()
    (sandbox.home / ".gitconfig.local").touch()
    workbench = sandbox.home / "code/public/workbench"
    (workbench / ".git").mkdir(parents=True)
    (workbench / "bin").mkdir()
    (workbench / "bin/workbench").symlink_to(sandbox.stub("workbench"))
    return sandbox, script


def test_installer_aborts_when_uv_bootstrap_fails(installer: tuple[ShellSandbox, Path]) -> None:
    sandbox, script = installer
    (sandbox.bin / "uv").unlink()

    result = sandbox.run(script)

    assert result.returncode != 0
    assert "uv" in result.stdout
    assert "Dotfiles setup complete" not in result.stdout
    assert "dock.sh" not in sandbox.log.read_text()


def test_installer_requires_uv_after_successful_bootstrap(
    installer: tuple[ShellSandbox, Path],
) -> None:
    sandbox, script = installer
    (sandbox.bin / "uv").unlink()
    sandbox.stub("curl")
    sandbox.stub("sh")

    result = sandbox.run(script)

    assert result.returncode != 0
    assert "uv is unavailable" in result.stdout
    assert "Dotfiles setup complete" not in result.stdout


@pytest.mark.parametrize("failure", ["packages", "python"])
def test_required_install_failure_prevents_completion(
    installer: tuple[ShellSandbox, Path], failure: str
) -> None:
    sandbox, script = installer
    (sandbox.bin / "python3.14").unlink()
    sandbox.env["FAIL_STEP"] = (
        f"run --project {script.parent}/cli dotfiles brew install"
        if failure == "packages"
        else "python install 3.14"
    )

    result = sandbox.run(script)

    assert result.returncode != 0
    assert "Dotfiles setup complete" not in result.stdout
    assert "Python 3.14 installed" not in result.stdout
    assert "workbench sync" not in sandbox.log.read_text()


def test_optional_pnpm_failure_warns_without_aborting(installer: tuple[ShellSandbox, Path]) -> None:
    sandbox, script = installer
    sandbox.stub("fnm", '[[ "$1" != list ]] || echo lts-latest')
    sandbox.stub("node")
    sandbox.stub("npx", "exit 1")

    result = sandbox.run(script)

    assert result.returncode == 0, result.stderr
    assert "pnpm could not be installed" in result.stdout
    assert "Dotfiles setup complete" in result.stdout


def test_installer_success_and_rerun_reconcile_required_steps(
    installer: tuple[ShellSandbox, Path],
) -> None:
    sandbox, script = installer
    for _ in range(2):
        result = sandbox.run(script)
        assert result.returncode == 0, result.stderr
        assert "Dotfiles setup complete" in result.stdout
    commands = sandbox.log.read_text()
    assert commands.count("dotfiles brew install") == 2
    assert commands.count("workbench sync all") == 2
    assert commands.count("workbench drift all") == 2


@pytest.mark.parametrize("retry_succeeds", [False, True])
def test_ssh_key_add_reports_the_retry_result(tmp_path: Path, retry_succeeds: bool) -> None:
    sandbox = ShellSandbox(tmp_path)
    sandbox.allow("dirname", "mkdir", "chmod", "cat", "grep", "awk")
    sandbox.stub("git", "echo test@example.invalid")
    sandbox.stub("pgrep")
    sandbox.stub("ssh-agent", "echo ':'")
    sandbox.stub("ssh-keygen", "echo '256 SHA256:test test@example.invalid'")
    sandbox.stub("ssh", "echo successfully authenticated")
    sandbox.stub(
        "ssh-add",
        '[[ "$1" != -l ]] || exit 1\n'
        'if [[ -f "$HOME/add-attempt" && "$RETRY_SUCCEEDS" == yes ]]; then exit 0; fi\n'
        ': > "$HOME/add-attempt"\nexit 1',
    )
    sandbox.env["RETRY_SUCCEEDS"] = "yes" if retry_succeeds else "no"
    (sandbox.home / ".gitconfig.local").touch()
    ssh_dir = sandbox.home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").touch()
    (ssh_dir / "id_ed25519.pub").touch()

    result = sandbox.run(ROOT / "macos/ssh.sh")

    assert result.returncode == 0, result.stderr
    assert ("SSH key added to ssh-agent" in result.stdout) is retry_succeeds
    assert ("Could not add key to ssh-agent" in result.stdout) is not retry_succeeds
    assert sandbox.log.read_text().count("ssh-add --apple-use-keychain") == 2


_OMLX_REVISION = "14c285372cbdb1777adea5bb49087ced0bffc0b5"


@pytest.fixture
def omlx(tmp_path: Path) -> ShellSandbox:
    sandbox = ShellSandbox(tmp_path)
    sandbox.allow("dirname", "mkdir", "mktemp", "rm", "cp", "jq", "cmp", "install", "touch")
    prefix = tmp_path / "omlx"
    (prefix / "libexec/bin").mkdir(parents=True)
    (prefix / "libexec/bin/python").symlink_to(
        sandbox.stub("python", 'exit "${GRAMMAR_STATUS:-0}"')
    )
    (prefix / "libexec/bin/hf").symlink_to(sandbox.stub("hf"))
    sandbox.env["OMLX_PREFIX"] = str(prefix)
    sandbox.stub(
        "brew",
        'case "$*" in\n'
        '  "--prefix omlx") echo "$OMLX_PREFIX";;\n'
        '  "services restart jundot/omlx/omlx")\n'
        '    [[ "${RESTART_FAILS:-no}" == no ]] || exit 1\n'
        '    echo healthy > "$HOME/service-state";;\n'
        '  "reinstall jundot/omlx/omlx --with-grammar") exit 1;;\n'
        "  *) exit 99;;\nesac",
    )
    sandbox.stub(
        "curl",
        '[[ "$*" == *http://127.0.0.1:8000/health* ]] || exit 99\n'
        '[[ "${HEALTH_FAILS:-no}" == no && "$(< "$HOME/service-state")" == healthy ]] || exit 7\n'
        'if [[ -n "${HEALTH_BODY+x}" ]]; then printf "%s" "$HEALTH_BODY"; '
        'else echo \'{"status":"healthy","engine_pool":{"model_count":1}}\'; fi',
    )
    (sandbox.home / "service-state").write_text("healthy\n")
    model = sandbox.home / ".omlx/models/Jundot/Qwen3.6-35B-A3B-oQ4e-mtp"
    model.mkdir(parents=True)
    (model / "model.safetensors.index.json").write_text("{}")
    for shard in range(1, 6):
        (model / f"model-{shard:05}-of-00005.safetensors").write_text("weights")
    (model / ".dotfiles-revision").write_text(f"{_OMLX_REVISION}\n")
    return sandbox


def test_omlx_restarts_an_unchanged_but_stopped_service(omlx: ShellSandbox) -> None:
    script = ROOT / "macos/configure-omlx.sh"
    assert omlx.run(script).returncode == 0
    omlx.log.write_text("")
    (omlx.home / "service-state").write_text("stopped\n")

    result = omlx.run(script)

    assert result.returncode == 0, result.stderr
    assert "services restart" in omlx.log.read_text()
    assert "oMLX ready" in result.stdout


def test_omlx_retries_failed_restart_even_with_old_service_healthy(omlx: ShellSandbox) -> None:
    script = ROOT / "macos/configure-omlx.sh"
    omlx.env["RESTART_FAILS"] = "yes"

    failed = omlx.run(script)

    assert failed.returncode != 0
    assert "oMLX ready" not in failed.stdout
    omlx.env["RESTART_FAILS"] = "no"
    omlx.log.write_text("")

    recovered = omlx.run(script)

    assert recovered.returncode == 0, recovered.stderr
    assert "services restart" in omlx.log.read_text()
    assert "oMLX ready" in recovered.stdout


@pytest.mark.parametrize("empty", [False, True])
def test_omlx_rejects_incomplete_weights_after_download(omlx: ShellSandbox, empty: bool) -> None:
    shard = next((omlx.home / ".omlx/models").rglob("model-00001-*.safetensors"))
    if empty:
        shard.write_text("")
    else:
        shard.unlink()

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode != 0
    assert "oMLX ready" not in result.stdout
    assert "hf download" in omlx.log.read_text()
    assert "services restart" not in omlx.log.read_text()


def test_omlx_healthy_rerun_preserves_settings_without_restart(omlx: ShellSandbox) -> None:
    settings = omlx.home / ".omlx/settings.json"
    settings.write_text('{"auth": {"api_key": "test-value"}, "future": {"enabled": true}}')
    script = ROOT / "macos/configure-omlx.sh"
    first = omlx.run(script)
    assert first.returncode == 0, first.stderr
    stat = settings.stat()
    omlx.log.write_text("")

    result = omlx.run(script)

    assert result.returncode == 0, result.stderr
    assert "services restart" not in omlx.log.read_text()
    assert "hf download" not in omlx.log.read_text()
    assert "curl" in omlx.log.read_text()
    assert settings.stat().st_mtime_ns == stat.st_mtime_ns
    assert stat.st_mode & 0o777 == 0o600
    merged = json.loads(settings.read_text())
    assert merged["auth"] == {"api_key": "test-value"}
    assert merged["future"] == {"enabled": True}
    assert merged["model"]["model_dir"] == str(omlx.home / ".omlx/models")
    assert not (omlx.home / ".omlx/.restart-required").exists()


def test_omlx_health_failure_does_not_claim_readiness_and_retries(omlx: ShellSandbox) -> None:
    script = ROOT / "macos/configure-omlx.sh"
    omlx.env["HEALTH_FAILS"] = "yes"

    failed = omlx.run(script)

    assert failed.returncode != 0
    assert "did not become healthy" in failed.stderr
    assert "oMLX ready" not in failed.stdout
    omlx.env["HEALTH_FAILS"] = "no"
    omlx.log.write_text("")
    recovered = omlx.run(script)
    assert recovered.returncode == 0, recovered.stderr
    assert "services restart" in omlx.log.read_text()


@pytest.mark.parametrize("contents", ["{broken", "[]", "null"])
def test_omlx_invalid_settings_are_preserved_and_abort(omlx: ShellSandbox, contents: str) -> None:
    settings = omlx.home / ".omlx/settings.json"
    settings.write_text(contents)

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode != 0
    assert settings.read_text() == contents
    assert "oMLX ready" not in result.stdout
    assert "services restart" not in omlx.log.read_text()


def test_omlx_grammar_install_failure_prevents_readiness(omlx: ShellSandbox) -> None:
    omlx.env["GRAMMAR_STATUS"] = "1"

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode != 0
    assert "brew reinstall" in omlx.log.read_text()
    assert "services restart" not in omlx.log.read_text()
    assert "oMLX ready" not in result.stdout


def test_omlx_download_repairs_partial_model_before_restart(omlx: ShellSandbox) -> None:
    shard = next((omlx.home / ".omlx/models").rglob("model-00001-*.safetensors"))
    shard.unlink()
    omlx.stub("hf", 'printf weights > "$6/model-00001-of-00005.safetensors"')

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode == 0, result.stderr
    assert shard.read_text() == "weights"
    commands = omlx.log.read_text()
    assert (
        f"hf download Jundot/Qwen3.6-35B-A3B-oQ4e-mtp --revision {_OMLX_REVISION}"
        in commands
    )
    assert commands.index("hf download") < commands.index("services restart")
    assert "oMLX ready" in result.stdout


def test_omlx_complete_unpinned_model_is_reconciled_to_revision(omlx: ShellSandbox) -> None:
    revision = next((omlx.home / ".omlx/models").rglob(".dotfiles-revision"))
    revision.unlink()

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode == 0, result.stderr
    assert revision.read_text() == f"{_OMLX_REVISION}\n"
    assert f"--revision {_OMLX_REVISION}" in omlx.log.read_text()


def test_omlx_loader_repair_preserves_existing_record_entries() -> None:
    script = (ROOT / "macos/configure-omlx.sh").read_text()

    assert "printf 'xgrammar/libxgrammar_bindings.dylib,,\\n' >> \"$record\"" in script
    assert "printf 'xgrammar/libxgrammar_bindings.dylib,,\\n' > \"$record\"" not in script


@pytest.mark.parametrize(
    "body",
    [
        "",
        "<html>ok</html>",
        "{}",
        '{"status":"healthy"}',
        '{"status":"healthy","engine_pool":{"model_count":0}}',
        '{"status":"loading","engine_pool":{"model_count":1}}',
    ],
)
def test_omlx_rejects_unrelated_health_responses(omlx: ShellSandbox, body: str) -> None:
    omlx.env["HEALTH_BODY"] = body

    result = omlx.run(ROOT / "macos/configure-omlx.sh")

    assert result.returncode != 0
    assert "oMLX ready" not in result.stdout
