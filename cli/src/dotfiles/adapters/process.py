"""Real subprocess implementation of the ProcessRunner port."""

import subprocess
from collections.abc import Mapping, Sequence

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
    ) -> CommandResult:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=check,
            env=dict(env) if env is not None else None,
            input=stdin,
        )
        return CommandResult(
            command=tuple(command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
