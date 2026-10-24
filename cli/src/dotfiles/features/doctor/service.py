"""`dotfiles doctor` checks. Pure over ProcessRunner port + direct pathlib."""

import os
import re
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotfiles.features.credential.models import CredentialRecord
from dotfiles.features.credential.service import CredentialInventoryError, CredentialService
from dotfiles.features.doctor.models import CheckResult, InferenceHealth
from dotfiles.features.packages.homebrew import InstallPlan
from dotfiles.features.packages.manifest import (
    ALL_FLAGS,
    PackageInventoryError,
    PackageManifest,
    enabled_packages,
)
from dotfiles.features.packages.service import runtime_tool_drift
from dotfiles.features.remote.service import RemoteService
from dotfiles.host import REPO_ROOT, RUNTIMES, ManagedLink, managed_links, resolve_profile
from dotfiles.ports import ProcessRunner


def _make_symlink(src: Path, dest: Path) -> None:
    """Create dest -> src symlink, replacing any existing link at dest.

    A regular file at dest (someone's hand-rolled config) is renamed to a
    .backup sibling instead of being deleted — --fix must not destroy data.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        dest.unlink()
    elif dest.exists():
        backup = dest.with_name(dest.name + ".backup")
        counter = 1
        while backup.exists() or backup.is_symlink():
            backup = dest.with_name(f"{dest.name}.backup.{counter}")
            counter += 1
        dest.rename(backup)
    dest.symlink_to(src)


# Version probes supplement package inventory: (display name, command, package).
_TOOL_CHECKS: dict[str, tuple[tuple[str, str, str | None], ...]] = {
    "Core Tools": (
        ("Homebrew", "brew", None),
        ("Git", "git", "git"),
        ("jq", "jq", "jq"),
        ("yq", "yq", "yq"),
    ),
    "Editors": (("Zed", "zed", "zed"),),
    "Dev Tools": (
        ("Just", "just", "just"),
        ("Delta", "delta", "git-delta"),
        ("golangci-lint", "golangci-lint", "golangci-lint"),
    ),
}


def _credential_needs_attention(record: CredentialRecord) -> bool:
    return record.status in {"expired", "inaccessible"} or (
        record.spec.required and record.status == "missing"
    )


def _notes_launcher(home: Path) -> Path | None:
    """Match install.sh: explicit override, otherwise the first executable primary checkout."""
    root = os.environ.get("PRIVATE_AUTOMATION_ROOT")
    candidates = (
        [Path(root) / "bin" / "notes"]
        if root
        else [
            path
            for path in sorted((home / "code" / "private").glob("*/bin/notes"))
            if (path.parent.parent / ".git").is_dir()
        ]
    )
    return next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)


class DoctorService:
    """Produces a list[CheckResult] representing the health of the dotfiles install."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        home: Path,
        dotfiles_dir: Path,
        fix: bool,
        profile: str | None = None,
        which: Callable[[str], str | None] = shutil.which,
        apps_dir: Path = Path("/Applications"),
        brew_bin: Path = Path("/opt/homebrew/bin"),
    ) -> None:
        self._runner = runner
        self._home = home
        self._dotfiles = dotfiles_dir
        self._fix = fix
        self._profile = resolve_profile(home, profile)
        manifest_path = dotfiles_dir / "config/packages.toml"
        self._manifest = PackageManifest.load(manifest_path) if manifest_path.exists() else None
        selection = self._manifest or PackageManifest.load(REPO_ROOT / "config/packages.toml")
        self._wanted = {
            name
            for name, _kind in enabled_packages(
                selection, flags_on=ALL_FLAGS, profile=self._profile
            )
        }
        self._which = which
        # System install locations — injected so the .app / homebrew-symlink
        # checks are testable under tmp_path instead of the real machine.
        self._apps_dir = apps_dir
        self._brew_bin = brew_bin

    def _tool(self, section: str, name: str, cmd: str, hint: str) -> CheckResult:
        """Check a CLI tool via shutil.which; detail = first line of --version."""
        if self._which(cmd) is not None:
            return self._probe(
                section, name, (cmd, "version" if cmd == "go" else "--version"), hint
            )
        return CheckResult(section=section, name=name, status="missing", hint=hint)

    def _probe(self, section: str, name: str, command: tuple[str, ...], hint: str) -> CheckResult:
        result = self._runner.run(command, timeout=10)
        if result.ok:
            detail = result.stdout.splitlines()[0].strip() if result.stdout.strip() else "installed"
            return CheckResult(section=section, name=name, status="ok", detail=detail, hint=hint)
        detail = result.stderr.strip() or f"probe failed (exit {result.exit_code})"
        return CheckResult(section=section, name=name, status="warn", detail=detail, hint=hint)

    def _symlink(self, section: str, name: str, src: Path, dest: Path) -> CheckResult:
        """Check (and optionally fix) a symlink from dest -> src."""
        if not src.exists():
            return CheckResult(
                section=section,
                name=name,
                status="missing",
                detail="managed source is missing",
                hint="Restore the source in the dotfiles checkout",
            )
        if dest.is_symlink() and dest.resolve(strict=False) == src.resolve(strict=False):
            return CheckResult(section=section, name=name, status="ok", detail="symlinked")
        if self._fix:
            _make_symlink(src, dest)
            return CheckResult(section=section, name=name, status="fixed", detail="symlinked")
        return CheckResult(section=section, name=name, status="missing", hint="not symlinked")

    def run(self) -> list[CheckResult]:
        """Run all checks, grouped by section.

        Sections run concurrently (each is dominated by independent
        `<tool> --version` subprocesses) and are reassembled in order, so the
        rendered report is byte-identical to a sequential run.
        """
        sections: tuple[Callable[[], list[CheckResult]], ...] = (
            self._check_core_tools,
            self._check_essentials,
            self._check_editors,
            self._check_runtimes,
            self._check_ai_tools,
            self._check_credentials,
            self._check_packages,
            self._check_local_inference,
            self._check_dev_tools,
            self._check_remote_continuity,
            self._check_configuration,
        )

        def _run_section(check: Callable[[], list[CheckResult]]) -> list[CheckResult]:
            return check()

        with ThreadPoolExecutor(max_workers=len(sections)) as pool:
            grouped = list(pool.map(_run_section, sections))
        return [result for group in grouped for result in group]

    # ------------------------------------------------------------------ #
    # Section helpers
    # ------------------------------------------------------------------ #

    def _check_core_tools(self) -> list[CheckResult]:
        return self._tools("Core Tools")

    def _tools(self, section: str) -> list[CheckResult]:
        return [
            self._tool(
                section,
                name,
                cmd,
                "Run: dotfiles install"
                if package is None
                else f"Run: dotfiles brew install --profile {self._profile}",
            )
            for name, cmd, package in _TOOL_CHECKS[section]
            if package is None or package in self._wanted
        ]

    def _check_essentials(self) -> list[CheckResult]:
        sec = "Essentials"
        if "tailscale-app" not in self._wanted:
            return []
        tailscale_path = self._apps_dir / "Tailscale.app"
        if self._which("tailscale") is not None or tailscale_path.exists():
            return [CheckResult(section=sec, name="Tailscale", status="ok", detail="installed")]
        return [
            CheckResult(
                section=sec,
                name="Tailscale",
                status="missing",
                hint="brew install --cask tailscale-app",
            )
        ]

    def _check_editors(self) -> list[CheckResult]:
        return self._tools("Editors")

    def _check_runtimes(self) -> list[CheckResult]:
        sec = "Runtimes"
        results: list[CheckResult] = [
            self._tool(sec, "FNM", "fnm", "brew install fnm"),
            self._tool(sec, "UV", "uv", "brew install uv"),
        ]
        if "go" in self._wanted:
            results.append(self._tool(sec, "Go", "go", "brew install go"))
        if self._profile == "personal":
            pnpm = self._tool(sec, "pnpm", "pnpm", "Run: dotfiles install")
            results.append(self._require_version(pnpm, RUNTIMES.pnpm, ""))
        results.extend(self._check_node(sec))
        results.extend(self._check_python(sec))
        results.extend(self._check_node_symlink(sec))
        return results

    def _check_node(self, sec: str) -> list[CheckResult]:
        """Node.js via fnm — only checked if fnm present."""
        if self._which("fnm") is None:
            return []
        result = self._probe(
            sec,
            "Node.js",
            ("node", "--version"),
            f"Run: fnm use --install-if-missing {RUNTIMES.node}",
        )
        return [self._require_version(result, RUNTIMES.node, "v")]

    @staticmethod
    def _require_version(result: CheckResult, wanted: str, prefix: str) -> CheckResult:
        if result.status == "ok" and not re.match(
            re.escape(prefix + wanted) + r"(?:\.|$)", result.detail
        ):
            return result.model_copy(update={"status": "warn"})
        return result

    def _check_python(self, sec: str) -> list[CheckResult]:
        """Find the declared interpreter without allowing uv to download it."""
        hint = f"Run: uv python install {RUNTIMES.python}"
        if self._which("uv") is not None:
            return self._check_uv_python(sec)
        command = next(
            (name for name in (f"python{RUNTIMES.python}", "python3") if self._which(name)),
            None,
        )
        if command is None:
            return [CheckResult(section=sec, name="Python", status="missing", hint=hint)]
        result = self._probe(sec, "Python", (command, "--version"), hint)
        return [self._require_version(result, RUNTIMES.python, "Python ")]

    def _check_uv_python(self, sec: str) -> list[CheckResult]:
        hint = f"Run: uv python install {RUNTIMES.python}"
        located = self._runner.run(("uv", "python", "find", RUNTIMES.python), timeout=10)
        if not located.ok or not located.stdout.strip():
            return [
                CheckResult(
                    section=sec,
                    name="Python",
                    status="warn",
                    detail=located.stderr.strip() or "declared interpreter not found",
                    hint=hint,
                )
            ]
        result = self._probe(sec, "Python", (located.stdout.strip(), "--version"), hint)
        return [self._require_version(result, RUNTIMES.python, "Python ")]

    def _check_node_symlink(self, sec: str) -> list[CheckResult]:
        """Node symlink at /opt/homebrew/bin/node — only if fnm present."""
        if self._profile == "work" or self._which("fnm") is None:
            return []
        node_link = self._brew_bin / "node"
        if node_link.is_symlink() and node_link.exists():
            return [
                CheckResult(
                    section=sec,
                    name="Node symlink",
                    status="ok",
                    detail="symlinked for GUI apps",
                )
            ]
        node_path = self._which("node")
        if self._fix and node_path is not None:
            node_bin = Path(node_path)
            npx_bin_str = self._which("npx")
            _make_symlink(node_bin, node_link)
            if npx_bin_str is not None:
                _make_symlink(Path(npx_bin_str), self._brew_bin / "npx")
            return [CheckResult(section=sec, name="Node symlink", status="fixed", detail="fixed")]
        return [
            CheckResult(
                section=sec,
                name="Node symlink",
                status="missing",
                hint="Run: dotfiles install (or --fix)",
            )
        ]

    def _check_ai_tools(self) -> list[CheckResult]:
        sec = "AI Tools"
        results: list[CheckResult] = [
            self._tool(
                sec,
                "Claude Code",
                "claude",
                "brew install --cask claude-code",
            ),
        ]
        if "codex" in self._wanted:
            results.append(self._tool(sec, "Codex", "codex", "brew install --cask codex"))
        results.extend(self._check_workbench(sec))
        return results

    def _check_workbench(self, sec: str) -> list[CheckResult]:
        """Run workbench's live desired-state reconciliation when available."""
        hint = "Run: workbench sync"
        if self._profile == "work":
            hint += " all --profile work"
        command = self._which("workbench")
        if command is None:
            candidate = self._home / "code" / "public" / "workbench" / "bin" / "workbench"
            command = str(candidate) if candidate.exists() else None
        if command is None:
            return [
                CheckResult(
                    section=sec,
                    name="Workbench",
                    status="missing",
                    hint=f"Clone ~/code/public/workbench, then {hint}",
                )
            ]

        args = (command, "drift", "all")
        if self._profile != "personal":
            args += ("--profile", self._profile)
        checked = self._runner.run(args, timeout=30)
        if checked.ok:
            return [
                CheckResult(
                    section=sec,
                    name="Workbench",
                    status="ok",
                    detail="managed agent config matches",
                )
            ]
        detail = next(
            (line.strip() for line in checked.stdout.splitlines() if line.strip()),
            "managed agent config has drifted",
        )
        return [
            CheckResult(
                section=sec,
                name="Workbench",
                status="warn",
                detail=detail,
                hint=hint,
            )
        ]

    def _check_credentials(self) -> list[CheckResult]:
        sec = "Credentials"
        try:
            records = CredentialService(runner=self._runner, home=self._home).list()
        except CredentialInventoryError as exc:
            return [
                CheckResult(
                    section=sec,
                    name="Inventory",
                    status="warn",
                    detail=str(exc),
                    hint="Run: dotfiles credential init",
                )
            ]
        problems = [record for record in records if _credential_needs_attention(record)]
        stored = sum(record.status == "stored" for record in records)
        resolved = sum(record.status in {"stored", "superseded", "deferred"} for record in records)
        if problems:
            ids = ", ".join(record.spec.id for record in problems)
            return [
                CheckResult(
                    section=sec,
                    name="Inventory",
                    status="warn",
                    detail=(
                        f"{resolved}/{len(records)} resolved ({stored} stored); attention: {ids}"
                    ),
                    hint="Run: dotfiles credential list",
                )
            ]
        return [
            CheckResult(
                section=sec,
                name="Inventory",
                status="ok",
                detail=f"{resolved}/{len(records)} resolved ({stored} stored)",
            )
        ]

    def _check_packages(self) -> list[CheckResult]:
        sec = "Packages"
        hint = f"Run: dotfiles brew install --profile {self._profile}"
        if self._manifest is None:
            return [
                CheckResult(
                    section=sec,
                    name="Inventory",
                    status="warn",
                    detail="package manifest not found",
                )
            ]
        try:
            plan = InstallPlan.compute(
                self._manifest, self._runner, flags_on=ALL_FLAGS, profile=self._profile
            )
            drift = [f"{name} (missing)" for name, _kind in plan.missing]
            drift.extend(runtime_tool_drift(self._manifest, self._runner, profile=self._profile))
        except PackageInventoryError as exc:
            return [
                CheckResult(
                    section=sec,
                    name="Inventory",
                    status="warn",
                    detail=str(exc),
                    hint="Retry: dotfiles brew stale",
                )
            ]
        if drift:
            return [
                CheckResult(
                    section=sec,
                    name="Desired software",
                    status="missing",
                    detail=", ".join(drift),
                    hint=hint,
                )
            ]
        return [
            CheckResult(
                section=sec,
                name="Desired software",
                status="ok",
                detail="selected packages and pins match",
            )
        ]

    def _check_local_inference(self) -> list[CheckResult]:
        if "omlx" not in self._wanted or self._which("omlx") is None:
            return []
        result = self._runner.run(
            (
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "2",
                "--max-time",
                "5",
                "http://127.0.0.1:8000/health",
            ),
            timeout=10,
        )
        try:
            healthy = result.ok and InferenceHealth.model_validate_json(result.stdout).ready
        except ValueError:
            healthy = False
        return [
            CheckResult(
                section="Local inference",
                name="oMLX",
                status="ok" if result.ok and healthy else "warn",
                detail="ready with loaded models"
                if result.ok and healthy
                else "not ready (optional service)",
                hint="Run: dotfiles brew install" if not healthy else "",
            )
        ]

    def _check_dev_tools(self) -> list[CheckResult]:
        return self._tools("Dev Tools")

    def _check_remote_continuity(self) -> list[CheckResult]:
        if "paseo" not in self._wanted:
            return []
        return self._check_remote_agents("Remote Continuity")

    def _check_remote_agents(self, sec: str) -> list[CheckResult]:
        """The parts of the remote stack that actually break: are the daemons alive?

        Warn (not fail) — remote access may be intentionally off. Skipped when
        Tailscale is absent, since the stack cannot be up without it.
        """
        if self._which("tailscale") is None and not (self._apps_dir / "Tailscale.app").exists():
            return []
        service = RemoteService(runner=self._runner, home=self._home)
        results: list[CheckResult] = []
        if service.paseo_running():
            detail = (
                "launch configuration drift — run: dfs remote on"
                if service.paseo_configuration_stale()
                else ""
            )
            status = "warn" if detail else "ok"
            results.append(
                CheckResult(
                    section=sec, name="Paseo daemon", status=status, detail=detail or "running"
                )
            )
        else:
            results.append(
                CheckResult(
                    section=sec,
                    name="Paseo daemon",
                    status="ok",
                    detail="stopped (optional; dfs remote on to start)",
                )
            )
        return results

    def _check_configuration(self) -> list[CheckResult]:
        sec = "Configuration"
        results = [
            self._check_link(sec, link) for link in managed_links() if self._link_enabled(link)
        ]
        if self._profile == "personal":
            configured = (self._home / ".gitconfig.local").exists()
            results.append(
                CheckResult(
                    section=sec,
                    name="Git identity",
                    status="ok" if configured else "warn",
                    detail="configured" if configured else "",
                    hint="Run install.sh to set up" if not configured else "",
                )
            )
            results.extend(self._check_notes_launchers(sec))
        return results

    def _link_enabled(self, link: ManagedLink) -> bool:
        if self._profile not in link.profiles:
            return False
        tool = link.required_tool
        if tool.startswith("app:"):
            name = tool.removeprefix("app:")
            return (self._apps_dir / f"{name}.app").exists() or self._which(
                name.lower()
            ) is not None
        return tool == "-" or self._which(tool) is not None

    def _check_link(self, sec: str, link: ManagedLink) -> CheckResult:
        return self._symlink(
            sec, link.label, self._dotfiles / link.source, self._home / link.destination
        )

    def _check_notes_launchers(self, sec: str) -> list[CheckResult]:
        """Check private Notes launchers when the vault is present."""
        source = _notes_launcher(self._home)
        if source is None:
            return []
        bin_dir = self._home / ".local" / "bin"
        results = [
            self._symlink(sec, "notes CLI", source, bin_dir / "notes"),
            self._symlink(sec, "nts alias", source, bin_dir / "nts"),
        ]
        # Apple Contacts remains an optional private projection; Apple Notes is blocked.
        bridge_source = source.parent / "apple-contacts"
        if bridge_source.is_file() and os.access(bridge_source, os.X_OK):
            results.append(
                self._symlink(sec, "apple-contacts", bridge_source, bin_dir / "apple-contacts")
            )
        return results
