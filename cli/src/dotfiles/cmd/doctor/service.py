"""`dotfiles doctor` checks. Pure over ProcessRunner port + direct pathlib."""

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.doctor.models import CheckResult
from dotfiles.fsutil import symlink as _make_symlink

# Declarative tool checks: (section, display name, command, install hint).
_TOOL_CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("Core Tools", "Homebrew", "brew", "Run install.sh"),
    ("Core Tools", "Git", "git", "brew install git"),
    ("Core Tools", "jq", "jq", "brew install jq"),
    ("Core Tools", "yq", "yq", "brew install yq"),
    ("Editors", "Zed", "zed", "brew install --cask zed"),
    ("Dev Tools", "Just", "just", "brew install just"),
    ("Dev Tools", "Delta", "delta", "brew install git-delta"),
    ("Dev Tools", "golangci-lint", "golangci-lint", "brew install golangci-lint"),
    ("Remote Shell", "Mosh", "mosh", "brew install mosh"),
    ("Remote Shell", "Zellij", "zellij", "brew install zellij"),
)


class DoctorService:
    """Produces a list[CheckResult] representing the health of the dotfiles install."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        home: Path,
        dotfiles_dir: Path,
        fix: bool,
        which: Callable[[str], str | None] = shutil.which,
        apps_dir: Path = Path("/Applications"),
        brew_bin: Path = Path("/opt/homebrew/bin"),
    ) -> None:
        self._runner = runner
        self._home = home
        self._dotfiles = dotfiles_dir
        self._fix = fix
        self._which = which
        # System install locations — injected so the .app / homebrew-symlink
        # checks are testable under tmp_path instead of the real machine.
        self._apps_dir = apps_dir
        self._brew_bin = brew_bin

    def _tool(self, section: str, name: str, cmd: str, hint: str) -> CheckResult:
        """Check a CLI tool via shutil.which; detail = first line of --version."""
        if self._which(cmd) is not None:
            result = self._runner.run((cmd, "--version"))
            detail = result.stdout.splitlines()[0].strip() if result.stdout.strip() else "installed"
            return CheckResult(section=section, name=name, status="ok", detail=detail)
        return CheckResult(section=section, name=name, status="missing", hint=hint)

    def _app(self, section: str, name: str, app_path: Path, hint: str) -> CheckResult:
        """Check a macOS .app bundle."""
        if app_path.exists():
            return CheckResult(section=section, name=name, status="ok", detail="installed")
        return CheckResult(section=section, name=name, status="missing", hint=hint)

    def _symlink(self, section: str, name: str, src: Path, dest: Path) -> CheckResult:
        """Check (and optionally fix) a symlink from dest -> src."""
        if dest.is_symlink() and dest.resolve(strict=False) == src.resolve(strict=False):
            return CheckResult(section=section, name=name, status="ok", detail="symlinked")
        if self._fix:
            _make_symlink(src, dest)
            return CheckResult(section=section, name=name, status="fixed", detail="symlinked")
        return CheckResult(section=section, name=name, status="missing", hint="not symlinked")

    def run(self) -> list[CheckResult]:
        """Run all checks in order, grouped by section."""
        results: list[CheckResult] = []
        results.extend(self._check_core_tools())
        results.extend(self._check_essentials())
        results.extend(self._check_editors())
        results.extend(self._check_runtimes())
        results.extend(self._check_ai_tools())
        results.extend(self._check_dev_tools())
        results.extend(self._check_remote_shell())
        results.extend(self._check_configuration())
        return results

    # ------------------------------------------------------------------ #
    # Section helpers
    # ------------------------------------------------------------------ #

    def _check_core_tools(self) -> list[CheckResult]:
        return [self._tool(sec, name, cmd, hint) for sec, name, cmd, hint in _TOOL_CHECKS[:4]]

    def _check_essentials(self) -> list[CheckResult]:
        sec = "Essentials"
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
        return [self._tool(sec, name, cmd, hint) for sec, name, cmd, hint in _TOOL_CHECKS[4:5]]

    def _check_runtimes(self) -> list[CheckResult]:
        sec = "Runtimes"
        results: list[CheckResult] = [
            self._tool(sec, "FNM", "fnm", "curl -fsSL https://fnm.vercel.app/install | bash"),
            self._tool(sec, "UV", "uv", "curl -LsSf https://astral.sh/uv/install.sh | sh"),
            self._tool(sec, "Go", "go", "brew install go"),
        ]
        results.extend(self._check_node(sec))
        results.extend(self._check_python(sec))
        results.extend(self._check_node_symlink(sec))
        return results

    def _check_node(self, sec: str) -> list[CheckResult]:
        """Node.js via fnm — only checked if fnm present."""
        if self._which("fnm") is None:
            return []
        fnm_result = self._runner.run(("fnm", "list"))
        fnm_out = fnm_result.stdout if fnm_result.ok else ""
        if "lts-latest" in fnm_out or "v" in fnm_out:
            node_result = self._runner.run(("node", "--version"))
            detail = node_result.stdout.strip() if node_result.ok else "not active"
            return [CheckResult(section=sec, name="Node.js", status="ok", detail=detail)]
        return [
            CheckResult(
                section=sec,
                name="Node.js",
                status="warn",
                hint="Run: fnm install --lts",
            )
        ]

    def _check_python(self, sec: str) -> list[CheckResult]:
        """Python — ok if 3.14, warn if only 3, missing otherwise."""
        if self._which("python3.14") is not None:
            result = self._runner.run(("python3.14", "--version"))
            detail = result.stdout.strip() if result.ok else "python3.14"
            return [CheckResult(section=sec, name="Python", status="ok", detail=detail)]
        if self._which("python3") is not None:
            result = self._runner.run(("python3", "--version"))
            detail = result.stdout.strip() if result.ok else "python3"
            return [
                CheckResult(
                    section=sec,
                    name="Python",
                    status="warn",
                    detail=detail,
                    hint="consider: uv python install 3.14",
                )
            ]
        return [
            CheckResult(
                section=sec,
                name="Python",
                status="missing",
                hint="Run: uv python install 3.14",
            )
        ]

    def _check_node_symlink(self, sec: str) -> list[CheckResult]:
        """Node symlink at /opt/homebrew/bin/node — only if fnm present."""
        if self._which("fnm") is None:
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
        if self._fix and self._which("node") is not None:
            node_bin = Path(self._which("node"))  # type: ignore[arg-type]
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
                "curl -fsSL https://claude.ai/install.sh | bash",
            ),
            self._tool(sec, "Codex", "codex", "brew install --cask codex"),
        ]
        results.extend(self._check_workbench(sec))
        return results

    def _check_workbench(self, sec: str) -> list[CheckResult]:
        """Run workbench's live desired-state reconciliation when available."""
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
                    hint="Clone ~/code/public/workbench, then run: workbench sync",
                )
            ]

        checked = self._runner.run((command, "check"))
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
                hint="Run: workbench sync",
            )
        ]

    def _check_dev_tools(self) -> list[CheckResult]:
        return [self._tool(sec, name, cmd, hint) for sec, name, cmd, hint in _TOOL_CHECKS[5:8]]

    def _check_remote_shell(self) -> list[CheckResult]:
        return [self._tool(sec, name, cmd, hint) for sec, name, cmd, hint in _TOOL_CHECKS[8:]]

    def _check_configuration(self) -> list[CheckResult]:
        sec = "Configuration"
        results: list[CheckResult] = []

        results.append(
            self._symlink(sec, ".zshrc", self._dotfiles / "shell" / ".zshrc", self._home / ".zshrc")
        )
        results.append(
            self._symlink(
                sec, ".gitconfig", self._dotfiles / "git" / ".gitconfig", self._home / ".gitconfig"
            )
        )
        results.append(
            self._symlink(
                sec, ".zprofile", self._dotfiles / "shell" / ".zprofile", self._home / ".zprofile"
            )
        )

        # Git identity (~/.gitconfig.local) — warn if absent
        gitconfig_local = self._home / ".gitconfig.local"
        if gitconfig_local.exists():
            results.append(
                CheckResult(section=sec, name="Git identity", status="ok", detail="configured")
            )
        else:
            results.append(
                CheckResult(
                    section=sec, name="Git identity", status="warn", hint="Run install.sh to set up"
                )
            )

        results.extend(self._check_ghostty(sec))
        results.extend(self._check_zellij(sec))
        results.extend(self._check_notes_launchers(sec))

        return results

    def _check_notes_launchers(self, sec: str) -> list[CheckResult]:
        """Check private Notes launchers when the vault is present."""
        source = self._home / "code" / "private" / "notes" / "bin" / "notes"
        if not source.exists():
            return []
        bin_dir = self._home / ".local" / "bin"
        return [
            self._symlink(sec, "notes CLI", source, bin_dir / "notes"),
            self._symlink(sec, "nts alias", source, bin_dir / "nts"),
        ]

    def _check_zellij(self, sec: str) -> list[CheckResult]:
        """Zellij config symlink — only when zellij is installed."""
        if self._which("zellij") is None:
            return []
        return [
            self._symlink(
                sec,
                "Zellij config",
                self._dotfiles / "terminal" / "zellij" / "config.kdl",
                self._home / ".config" / "zellij" / "config.kdl",
            )
        ]

    def _check_ghostty(self, sec: str) -> list[CheckResult]:
        """Ghostty config or app presence."""
        ghostty_config = self._home / ".config" / "ghostty" / "config"
        if ghostty_config.exists():
            return [CheckResult(section=sec, name="Ghostty", status="ok", detail="configured")]
        if (self._apps_dir / "Ghostty.app").exists():
            return [
                CheckResult(
                    section=sec,
                    name="Ghostty",
                    status="warn",
                    hint="Run install.sh to configure",
                )
            ]
        return []
