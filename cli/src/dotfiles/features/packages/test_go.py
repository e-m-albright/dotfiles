"""Pinned Go tool checks distinguish wrong versions from failed observation."""

import pytest

from dotfiles.features.packages.go import go_drift, install_go_tools
from dotfiles.features.packages.manifest import (
    GoPackage,
    PackageInventoryError,
    PackageManifest,
    Taps,
)
from dotfiles.testing.fakes import FakeProcessRunner


@pytest.fixture
def manifest():
    return PackageManifest(
        taps=Taps(),
        go_packages=[GoPackage(name="tool", module="example.com/tool", version="v1.2.3")],
    )


def located_runner(output="mod example.com/tool v1.2.3\n", exit_code=0):
    runner = FakeProcessRunner()
    runner.script(("which", "tool"), stdout="/home/dev/go/bin/tool\n")
    runner.script(
        ("go", "version", "-m", "/home/dev/go/bin/tool"), stdout=output, exit_code=exit_code
    )
    return runner


def test_failed_go_observation_is_not_version_drift(manifest):
    with pytest.raises(PackageInventoryError, match="Could not inspect"):
        go_drift(manifest, located_runner(exit_code=124))


def test_go_pin_matching_requires_exact_version(manifest):
    runner = located_runner("mod example.com/tool v1.2.30\n")
    assert go_drift(manifest, runner) == ["tool (want v1.2.3)"]
    install_go_tools(manifest, runner, dry_run=False)
    assert ("go", "install", "example.com/tool@v1.2.3") in runner.calls


def test_matching_go_pin_skips_install(manifest):
    runner = located_runner()
    assert go_drift(manifest, runner) == []
    assert install_go_tools(manifest, runner, dry_run=False)[0].level == "info"
    assert not any(call[:2] == ("go", "install") for call in runner.calls)


def test_go_dry_run_and_failed_install(manifest):
    runner = located_runner(exit_code=1)
    assert install_go_tools(manifest, runner, dry_run=True)[0].level == "info"
    assert runner.calls == []
    runner.script(("go", "install", "example.com/tool@v1.2.3"), exit_code=1)
    assert install_go_tools(manifest, runner, dry_run=False)[0].level == "error"
