"""Manifest-selected installers outside the ordinary package managers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from dotfiles.features.packages.manifest import (
    ALL_FLAGS,
    FeatureFlag,
    PackageManifest,
    SpecialInstaller,
    flag_active,
)
from dotfiles.ports import ProcessRunner
from dotfiles.result import StepResult


@dataclass(frozen=True)
class VerifiedDownload:
    path: Path | None
    error: str = ""


def _download_verified(
    runner: ProcessRunner, *, url: str, sha256: str, directory: Path, filename: str
) -> VerifiedDownload:
    target = directory / filename
    downloaded = runner.run(("curl", "-fsSL", "-o", str(target), url))
    if not downloaded.ok:
        detail = downloaded.stderr.strip() or f"curl exited {downloaded.exit_code}"
        return VerifiedDownload(None, f"download failed: {detail}")
    checked = runner.run(
        ("shasum", "-a", "256", "-c", "-"),
        stdin=f"{sha256}  {target}\n",
    )
    if checked.ok:
        return VerifiedDownload(target)
    actual = runner.run(("shasum", "-a", "256", str(target))).stdout.split(maxsplit=1)
    actual_hash = actual[0] if actual else "unavailable"
    return VerifiedDownload(None, f"expected {sha256}; downloaded {actual_hash}")


_RUSTUP_CHECK = ("sh", "-c", "command -v rustup || command -v cargo")
_RUSTUP_URL = "https://static.rust-lang.org/rustup/archive/1.28.2/aarch64-apple-darwin/rustup-init"
_RUSTUP_SHA256 = "20ef5516c31b1ac2290084199ba77dbbcaa1406c45c1d978ca68558ef5964ef5"


def install_rust(runner: ProcessRunner) -> list[StepResult]:
    """Install Rust via rustup if not already present.

    Idempotency guard: skips if `rustup` or `cargo` is on PATH.
    Shell startup already sources ``~/.cargo/env`` from the tracked ``.zshenv``;
    this installer must not write through the tracked ``.zprofile`` symlink.
    """
    check = runner.run(_RUSTUP_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="Rust already installed — skipping")]

    install_dir = Path(mkdtemp(prefix="dotfiles-rustup-"))
    try:
        download = _download_verified(
            runner,
            url=_RUSTUP_URL,
            sha256=_RUSTUP_SHA256,
            directory=install_dir,
            filename="rustup-init",
        )
        if download.path is None:
            return [
                StepResult(
                    level="error",
                    message="rustup download verification failed",
                    details=download.error,
                )
            ]
        runner.run(("chmod", "+x", str(download.path)))
        installed = runner.run((str(download.path), "-y"))
        if not installed.ok:
            return [StepResult(level="error", message="rustup installer failed")]
        return [StepResult(level="success", message="Rust installed via rustup")]
    finally:
        rmtree(install_dir)


def _install_special(
    name: str,
    installer: SpecialInstaller,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    if (
        installer.disabled
        or not flag_active(installer.flag, flags_on)
        or installer.method == "python_package"
    ):
        return []
    if dry_run:
        return [StepResult(level="info", message=f"DRY RUN: install {name}")]
    if installer.method == "rustup":
        return install_rust(runner)
    if installer.method == "omlx_setup":
        script = dotfiles_dir / "scripts" / "macos" / "omlx.sh"
        result = runner.run(("bash", str(script)))
        return [
            StepResult(
                level="success" if result.ok else "error",
                message="configure oMLX grammar, model, and service",
                details=result.stderr.strip(),
            )
        ]
    raise ValueError(f"Unsupported special installer method: {installer.method}")


def install_specials(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    """Run only the special installers declared and enabled by the manifest."""
    results: list[StepResult] = []
    selected = set(manifest.profiles[profile].specials) if profile != "personal" else None
    for name, installer in manifest.specials.items():
        if selected is not None and name not in selected:
            continue
        results.extend(
            _install_special(
                name,
                installer,
                runner,
                flags_on=ALL_FLAGS if selected is not None else flags_on,
                dotfiles_dir=dotfiles_dir,
                dry_run=dry_run,
            )
        )
    return results
