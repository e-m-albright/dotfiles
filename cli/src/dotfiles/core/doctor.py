"""`dotfiles doctor` checks. Pure over ProcessRunner port + direct pathlib."""

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.core.fsutil import symlink as _make_symlink
from dotfiles.core.models import CheckResult
from dotfiles.core.ports import ProcessRunner


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
    ) -> None:
        self._runner = runner
        self._home = home
        self._dotfiles = dotfiles_dir
        self._fix = fix
        self._which = which

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
        if dest.is_symlink() and str(src) in str(dest.readlink()):
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
        sec = "Core Tools"
        return [
            self._tool(sec, "Homebrew", "brew", "Run install.sh"),
            self._tool(sec, "Git", "git", "brew install git"),
            self._tool(sec, "jq", "jq", "brew install jq"),
            self._tool(sec, "yq", "yq", "brew install yq"),
        ]

    def _check_essentials(self) -> list[CheckResult]:
        sec = "Essentials"
        tailscale_path = Path("/Applications/Tailscale.app")
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
        sec = "Editors"
        return [
            self._tool(sec, "Cursor", "cursor", "brew install --cask cursor"),
            self._tool(sec, "Zed", "zed", "brew install --cask zed"),
        ]

    def _check_runtimes(self) -> list[CheckResult]:
        sec = "Runtimes"
        results: list[CheckResult] = [
            self._tool(sec, "Bun", "bun", "curl -fsSL https://bun.sh/install | bash"),
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
        node_link = Path("/opt/homebrew/bin/node")
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
                _make_symlink(Path(npx_bin_str), Path("/opt/homebrew/bin/npx"))
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
            )
        ]
        results.extend(self._check_gh_mcp(sec))
        return results

    def _check_gh_mcp(self, sec: str) -> list[CheckResult]:
        """gh-mcp extension — only checked if gh present."""
        if self._which("gh") is None:
            return []
        ext_result = self._runner.run(("gh", "extension", "list"))
        if ext_result.ok and "gh-mcp" in ext_result.stdout:
            return [CheckResult(section=sec, name="gh-mcp", status="ok", detail="installed")]
        if self._fix:
            install = self._runner.run(("gh", "extension", "install", "shuymn/gh-mcp"))
            if install.ok:
                return [CheckResult(section=sec, name="gh-mcp", status="fixed", detail="fixed")]
            return [
                CheckResult(
                    section=sec,
                    name="gh-mcp",
                    status="missing",
                    hint="gh auth login, then: gh extension install shuymn/gh-mcp",
                )
            ]
        return [
            CheckResult(
                section=sec,
                name="gh-mcp",
                status="missing",
                hint="Run: gh extension install shuymn/gh-mcp",
            )
        ]

    def _check_dev_tools(self) -> list[CheckResult]:
        sec = "Dev Tools"
        return [
            self._tool(sec, "Just", "just", "brew install just"),
            self._tool(sec, "Delta", "delta", "brew install git-delta"),
            self._tool(sec, "golangci-lint", "golangci-lint", "brew install golangci-lint"),
        ]

    def _check_remote_shell(self) -> list[CheckResult]:
        sec = "Remote Shell"
        results: list[CheckResult] = [
            self._tool(sec, "Mosh", "mosh", "brew install mosh"),
            self._tool(sec, "Zellij", "zellij", "brew install zellij"),
            self._app(
                sec, "Termius", Path("/Applications/Termius.app"), "brew install --cask termius"
            ),
        ]
        return results

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

        # Claude instructions (~/.claude/CLAUDE.md) — warn if absent
        claude_md = self._home / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            results.append(
                CheckResult(section=sec, name="Claude instructions", status="ok", detail="exists")
            )
        else:
            results.append(
                CheckResult(
                    section=sec,
                    name="Claude instructions",
                    status="warn",
                    hint="Run: dotfiles agent-setup",
                )
            )

        results.extend(self._check_claude_settings(sec))
        results.extend(self._check_claude_mcp(sec))
        results.extend(self._check_codex(sec))
        results.extend(self._check_ghostty(sec))

        return results

    def _jq_count(self, expr: str, path: Path) -> int:
        """Run jq expr against path; return parsed int or 0 on failure."""
        if not path.exists() or self._which("jq") is None:
            return 0
        result = self._runner.run(("jq", expr, str(path)))
        if result.ok and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
        return 0

    def _check_claude_settings(self, sec: str) -> list[CheckResult]:
        """Claude plugins + hooks from ~/.claude/settings.json."""
        settings = self._home / ".claude" / "settings.json"
        if not settings.exists() or self._which("jq") is None:
            return []
        results: list[CheckResult] = []

        plugin_count = self._jq_count(".enabledPlugins // {} | length", settings)
        if plugin_count > 0:
            results.append(
                CheckResult(
                    section=sec,
                    name="Claude plugins",
                    status="ok",
                    detail=f"{plugin_count} plugins enabled",
                )
            )
        else:
            results.append(
                CheckResult(
                    section=sec,
                    name="Claude plugins",
                    status="warn",
                    hint="Run: dotfiles agent-setup",
                )
            )

        hook_count = self._jq_count(".hooks // {} | keys | length", settings)
        if hook_count > 0:
            results.append(
                CheckResult(
                    section=sec,
                    name="Claude hooks",
                    status="ok",
                    detail=f"{hook_count} events configured",
                )
            )
        else:
            results.append(
                CheckResult(
                    section=sec,
                    name="Claude hooks",
                    status="warn",
                    hint="Run: dotfiles agent-setup",
                )
            )

        return results

    def _check_claude_mcp(self, sec: str) -> list[CheckResult]:
        """Claude MCP servers from ~/.claude.json."""
        claude_json = self._home / ".claude.json"
        if not claude_json.exists() or self._which("jq") is None:
            return []
        mcp_count = self._jq_count(".mcpServers // {} | length", claude_json)
        if mcp_count > 0:
            return [
                CheckResult(
                    section=sec, name="Claude MCP", status="ok", detail=f"{mcp_count} servers"
                )
            ]
        return [
            CheckResult(
                section=sec, name="Claude MCP", status="warn", hint="Run: dotfiles agent-setup"
            )
        ]

    def _check_codex(self, sec: str) -> list[CheckResult]:
        """Codex instructions/hooks/MCP — only if codex on PATH."""
        if self._which("codex") is None:
            return []
        results: list[CheckResult] = []

        agents_md = self._home / ".codex" / "AGENTS.md"
        if agents_md.exists():
            results.append(
                CheckResult(section=sec, name="Codex instructions", status="ok", detail="exists")
            )
        else:
            results.append(
                CheckResult(
                    section=sec,
                    name="Codex instructions",
                    status="warn",
                    hint="Run: dotfiles agent-setup",
                )
            )

        hooks_json = self._home / ".codex" / "hooks.json"
        if hooks_json.exists():
            results.append(
                CheckResult(section=sec, name="Codex hooks", status="ok", detail="configured")
            )
        else:
            results.append(
                CheckResult(
                    section=sec, name="Codex hooks", status="warn", hint="Run: dotfiles agent-setup"
                )
            )

        config_toml = self._home / ".codex" / "config.toml"
        toml_content = config_toml.read_text() if config_toml.exists() else ""
        if "mcp_servers" in toml_content:
            results.append(
                CheckResult(section=sec, name="Codex MCP", status="ok", detail="configured")
            )
        else:
            results.append(
                CheckResult(
                    section=sec, name="Codex MCP", status="warn", hint="Run: dotfiles agent-setup"
                )
            )

        return results

    def _check_ghostty(self, sec: str) -> list[CheckResult]:
        """Ghostty config or app presence."""
        ghostty_config = self._home / ".config" / "ghostty" / "config"
        if ghostty_config.exists():
            return [CheckResult(section=sec, name="Ghostty", status="ok", detail="configured")]
        if Path("/Applications/Ghostty.app").exists():
            return [
                CheckResult(
                    section=sec,
                    name="Ghostty",
                    status="warn",
                    hint="Run install.sh to configure",
                )
            ]
        return []
