from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def test_init_and_json_list(tmp_path: Path) -> None:
    context = make_fake_context(home=tmp_path)
    initialized = runner.invoke(app, ["credential", "init"], obj=context)
    assert initialized.exit_code == 0

    listed = runner.invoke(app, ["credential", "list", "--json"], obj=context)
    assert listed.exit_code == 0
    payload = json.loads(listed.stdout)
    assert [item["id"] for item in payload] == [
        "google-pi",
        "anthropic-pi",
        "openai-pi",
        "openrouter-pi",
    ]
    assert all("secret" not in item for item in payload)


def test_run_injects_only_declared_environment_into_child(tmp_path: Path, monkeypatch) -> None:
    process_runner = FakeProcessRunner()
    context = make_fake_context(runner=process_runner, home=tmp_path)
    assert runner.invoke(app, ["credential", "init"], obj=context).exit_code == 0
    command = (
        "security",
        "find-generic-password",
        "-s",
        "dotfiles.credential.pi.google",
        "-a",
        "api-key",
        "-w",
    )
    process_runner.script(command, stdout="test-value\n")
    executed: dict[str, object] = {}

    def fake_exec(file: str, args: list[str], env: dict[str, str]) -> None:
        executed.update(
            file=file,
            args=args,
            value=env["GEMINI_API_KEY"],
            inherited_openai="OPENAI_API_KEY" in env,
        )

    monkeypatch.setenv("OPENAI_API_KEY", "ambient-value")
    monkeypatch.setattr("dotfiles.cmd.credential.cli.os.execvpe", fake_exec)

    result = runner.invoke(
        app, ["credential", "run", "google-pi", "--", "python", "job.py"], obj=context
    )

    assert result.exit_code == 0
    assert executed == {
        "file": "python",
        "args": ["python", "job.py"],
        "value": "test-value",
        "inherited_openai": False,
    }


def test_human_list_renders_grants_status_consumers_and_access(tmp_path: Path) -> None:
    context = make_fake_context(home=tmp_path)
    assert runner.invoke(app, ["credential", "init"], obj=context).exit_code == 0

    result = runner.invoke(app, ["credential", "list"], obj=context)

    assert result.exit_code == 0
    assert "google-pi" in result.stdout
    assert "Consumer boundary" in result.stdout
    assert "Gemini API" in result.stdout


def test_commands_report_inventory_errors(tmp_path: Path) -> None:
    context = make_fake_context(home=tmp_path)

    missing = runner.invoke(app, ["credential", "list"], obj=context)
    assert missing.exit_code == 1
    assert "not initialized" in missing.stdout

    assert runner.invoke(app, ["credential", "init"], obj=context).exit_code == 0
    duplicate = runner.invoke(app, ["credential", "init"], obj=context)
    assert duplicate.exit_code == 1
    assert "already exists" in duplicate.stdout


def test_set_reports_interactive_enrollment(tmp_path: Path) -> None:
    context = make_fake_context(runner=FakeProcessRunner(), home=tmp_path)
    assert runner.invoke(app, ["credential", "init"], obj=context).exit_code == 0

    result = runner.invoke(app, ["credential", "set", "google-pi"], obj=context)

    assert result.exit_code == 0
    assert "stored in Keychain" in result.stdout


def test_link_pi_requires_explicit_force_for_replacement(tmp_path: Path) -> None:
    context = make_fake_context(home=tmp_path)
    assert runner.invoke(app, ["credential", "init"], obj=context).exit_code == 0
    auth = tmp_path / ".pi" / "agent" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"google": {"type": "api_key", "key": "existing"}}')
    auth.chmod(0o600)

    refused = runner.invoke(app, ["credential", "link-pi", "google-pi"], obj=context)
    assert refused.exit_code == 1
    assert "already configured" in refused.stdout

    linked = runner.invoke(app, ["credential", "link-pi", "google-pi", "--force"], obj=context)
    assert linked.exit_code == 0
