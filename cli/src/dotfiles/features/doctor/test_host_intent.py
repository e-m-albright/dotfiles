"""Doctor respects the same host intent as installation and reconciliation."""

from pathlib import Path

import pytest

from dotfiles.features.doctor.service import DoctorService
from dotfiles.testing.fakes import FakeProcessRunner


def service(tmp_path: Path, *, profile="personal", fix=False):
    home = tmp_path / "home"
    marker = home / ".config/dotfiles/profile"
    marker.parent.mkdir(parents=True)
    marker.write_text(profile + "\n")
    return DoctorService(
        runner=FakeProcessRunner(),
        home=home,
        dotfiles_dir=tmp_path / "repo",
        fix=fix,
        which=lambda name: "/bin/" + name,
        apps_dir=tmp_path / "apps",
        brew_bin=tmp_path / "brew",
    )


def test_work_fix_never_creates_personal_links(tmp_path):
    svc = service(tmp_path, profile="work", fix=True)
    checks = svc._check_configuration()
    names = {check.name for check in checks}
    assert ".gitconfig" not in names
    assert "Git identity" not in names
    assert "Zed settings" not in names
    assert not (tmp_path / "home/.gitconfig").exists()
    assert not (tmp_path / "home/.local/bin/notes").exists()


def test_missing_source_cannot_be_fixed_into_broken_link(tmp_path):
    svc = service(tmp_path, fix=True)
    dest = tmp_path / "home/.zshrc"
    check = svc._symlink("Configuration", "shell", tmp_path / "missing", dest)
    assert check.status == "missing"
    assert not dest.is_symlink()


def test_workbench_receives_active_profile(tmp_path):
    svc = service(tmp_path, profile="work")
    svc._check_workbench("AI Tools")
    assert ("/bin/workbench", "drift", "all", "--profile", "work") in svc._runner.calls
    svc._runner.script(("/bin/workbench", "drift", "all", "--profile", "work"), exit_code=1)
    check = svc._check_workbench("AI Tools")[0]
    assert check.hint == "Run: workbench sync all --profile work"


def test_node_wrong_major_is_not_healthy(tmp_path):
    svc = service(tmp_path)
    svc._runner.script(("fnm", "list"), stdout="v20.1.0\n")
    svc._runner.script(("node", "--version"), stdout="v20.1.0\n")
    check = svc._check_node("Runtimes")[0]
    assert check.status == "warn"
    assert "26" in check.hint


def test_package_inventory_failure_is_not_missing_packages(tmp_path):
    config = tmp_path / "repo/config/packages.toml"
    config.parent.mkdir(parents=True)
    config.write_text("[taps]\nlist=[]\n")
    svc = service(tmp_path)
    svc._runner.script(("brew", "list", "--formula", "-1"), exit_code=124, stderr="timed out")
    checks = svc._check_packages()
    assert len(checks) == 1
    assert checks[0].status == "warn"
    assert "timed out" in checks[0].detail


def test_work_skips_personal_services_and_runtime_repairs(tmp_path):
    svc = service(tmp_path, profile="work", fix=True)
    assert svc._check_remote_continuity() == []
    assert svc._check_local_inference() == []
    assert svc._check_node_symlink("Runtimes") == []
    assert "Go" not in {check.name for check in svc._check_runtimes()}
    assert "Codex" not in {check.name for check in svc._check_ai_tools()}


@pytest.mark.parametrize(
    ("payload", "exit_code", "status"),
    [
        ('{"status":"healthy","engine_pool":{"model_count":1,"other":"ignored"}}', 0, "ok"),
        ('{"status":"healthy","engine_pool":{"model_count":0}}', 0, "warn"),
        ('{"status":"loading","engine_pool":{"model_count":1}}', 0, "warn"),
        ('{"status":"healthy","engine_pool":{"model_count":true}}', 0, "warn"),
        ('{"status":"healthy","engine_pool":null}', 0, "warn"),
        ("invalid", 0, "warn"),
        ("{}", 7, "warn"),
    ],
)
def test_local_inference_readiness_is_bounded_and_read_only(tmp_path, payload, exit_code, status):
    svc = service(tmp_path)
    command = (
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "2",
        "--max-time",
        "5",
        "http://127.0.0.1:8000/health",
    )
    svc._runner.script(command, stdout=payload, exit_code=exit_code)
    checks = svc._check_local_inference()
    assert checks[0].status == status
    assert svc._runner.calls == [command]
    assert svc._runner.timeouts == [10]


def test_package_check_reports_drift_and_healthy_inventory(tmp_path):
    config = tmp_path / "repo/config/packages.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[taps]\nlist=[]\n[[section]]\nname="Core"\nkind="formula"\npackages=[{name="git"}]\n'
    )
    svc = service(tmp_path)
    assert svc._check_packages()[0].status == "missing"
    svc._runner.script(("brew", "list", "--formula", "-1"), stdout="git\n")
    assert svc._check_packages()[0].status == "ok"


def test_remote_service_stopped_is_not_a_health_warning(tmp_path):
    svc = service(tmp_path)
    checks = svc._check_remote_continuity()
    assert checks[0].status == "ok"
    assert "optional" in checks[0].detail


def test_pnpm_and_python_must_match_declared_versions(tmp_path):
    svc = service(tmp_path)
    svc._runner.script(("pnpm", "--version"), stdout="11.0.0\n")
    svc._runner.script(("uv", "python", "find", "3.14"), stdout="/managed/python\n")
    svc._runner.script(("/managed/python", "--version"), stdout="Python 3.13.0\n")
    checks = {check.name: check for check in svc._check_runtimes()}
    assert checks["pnpm"].status == "warn"
    assert checks["Python"].status == "warn"
