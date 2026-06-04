"""Interactive session launcher: fzf to pick, execvp to hand off to zellij."""

import os
import subprocess
from collections.abc import Sequence


class FzfExecLauncher:
    """Real SessionLauncher: fzf for selection, os.execvp to replace this process."""

    def pick(self, options: Sequence[str]) -> str | None:
        """Pick from `key<TAB>label` rows; fzf shows the label, we return the key.

        The label (after the first tab) is rendered with ANSI colour and is all
        that's displayed/searched; fzf echoes the whole row back, so the key in
        the first field is recovered untouched. A plain row (no tab) is its own key.
        """
        choices = list(options)
        if not choices:
            return None
        completed = subprocess.run(
            [
                "fzf",
                "--prompt",
                "session> ",
                "--height",
                "40%",
                "--reverse",
                "--ansi",
                "--delimiter",
                "\t",
                "--with-nth",
                "2..",
            ],
            input="\n".join(choices),
            text=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            return None
        selection = completed.stdout.strip()
        return selection.split("\t", 1)[0] if selection else None

    def attach(self, command: Sequence[str]) -> None:
        args = list(command)
        if not args:
            raise ValueError("attach: command must be non-empty")
        os.execvp(args[0], args)  # replaces this process; does not return
