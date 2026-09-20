"""Real subprocess implementation of the ProcessRunner port."""

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from dotfiles.adapters.ports import CommandResult


class SubprocessRunner:
    """Runs commands via subprocess.run, capturing output."""

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        cwd: Path | None = None,
        capture_output: bool = True,
        timeout: float | None = None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                list(command),
                capture_output=capture_output,
                text=True,
                check=False,
                env=dict(env) if env is not None else None,
                input=stdin,
                cwd=cwd,
                timeout=timeout,
            )
            result = CommandResult(
                command=tuple(command),
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except (FileNotFoundError, PermissionError) as exc:
            result = CommandResult(
                command=tuple(command),
                exit_code=127 if isinstance(exc, FileNotFoundError) else 126,
                stdout="",
                stderr=str(exc),
            )
        except subprocess.TimeoutExpired as exc:
            # TimeoutExpired output is bytes even when text=True.
            result = CommandResult(
                command=tuple(command),
                exit_code=124,
                stdout=_text(exc.stdout),
                stderr=f"Command timed out after {timeout}s. {_text(exc.stderr)}".strip(),
            )
        if check and not result.ok:
            raise subprocess.CalledProcessError(
                result.exit_code, list(command), output=result.stdout, stderr=result.stderr
            )
        return result


def _text(output: str | bytes | None) -> str:
    return output.decode(errors="replace") if isinstance(output, bytes) else output or ""
