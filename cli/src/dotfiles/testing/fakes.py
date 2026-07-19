"""In-memory fakes implementing application ports. Tests only."""

import subprocess
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

from dotfiles.adapters.ports import CommandResult
from dotfiles.app.context import AppContext
from dotfiles.cmd.email.icloud import parse_icloud_mask
from dotfiles.cmd.email.service import Mask, ReservedMask
from dotfiles.settings import Settings


class FakeProcessRunner:
    """Records calls; returns scripted results, defaulting to empty success."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.calls_with_input: list[tuple[tuple[str, ...], str | None]] = []
        self.inputs: list[str | None] = []
        self.cwds: list[Path | None] = []
        self._scripted: dict[tuple[str, ...], CommandResult] = {}

    def script(
        self,
        command: Sequence[str],
        *,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        key = tuple(command)
        self._scripted[key] = CommandResult(
            command=key, exit_code=exit_code, stdout=stdout, stderr=stderr
        )

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> CommandResult:
        key = tuple(command)
        self.calls.append(key)
        self.inputs.append(stdin)
        self.cwds.append(cwd)
        self.calls_with_input.append((key, stdin))
        result = self._scripted.get(
            key, CommandResult(command=key, exit_code=0, stdout="", stderr="")
        )
        if check and result.exit_code != 0:
            raise subprocess.CalledProcessError(
                result.exit_code, list(key), output=result.stdout, stderr=result.stderr
            )
        return result


class FakeMaskProvider:
    """In-memory MaskProvider: records calls, returns a scripted address + reserve result."""

    def __init__(
        self,
        *,
        address: str | None = "abc123xyz@icloud.com",
        anonymous_id: str | None = "anon-1",
        existing: Sequence[Mapping[str, object]] | None = None,
    ) -> None:
        self.address = address
        self.anonymous_id = anonymous_id
        self.existing = list(existing or [])
        self.generated = 0
        self.reserved: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.deactivated: list[str] = []

    def generate(self) -> str | None:
        self.generated += 1
        return self.address

    def reserve(self, email: str, label: str) -> ReservedMask:
        self.reserved.append((email, label))
        return ReservedMask(address=email, label=label, anonymous_id=self.anonymous_id)

    def __iter__(self) -> Iterator[Mask]:
        return (parse_icloud_mask(record) for record in self.existing)

    def delete(self, anonymous_id: str) -> Mapping[str, object]:
        self.deleted.append(anonymous_id)
        return {}

    def deactivate(self, anonymous_id: str) -> Mapping[str, object]:
        self.deactivated.append(anonymous_id)
        return {}


class FakeSessionLauncher:
    """Records pick/attach calls; returns a scripted selection."""

    def __init__(self, selection: str | None = None) -> None:
        self.selection = selection
        self.picked: list[list[str]] = []
        self.attached: list[list[str]] = []

    def pick(self, options: Sequence[str]) -> str | None:
        # Mirror FzfExecLauncher's `key<TAB>label` contract: record the keys (the
        # first tab-field) so tests assert on session names, not the ANSI labels.
        self.picked.append([o.split("\t", 1)[0] for o in options])
        return self.selection

    def attach(self, command: Sequence[str]) -> None:
        self.attached.append(list(command))


def write_tree(base: Path, spec: dict[str, str | None]) -> None:
    """Create files/dirs under base. value=str writes a file; value=None makes a dir."""
    for rel, content in spec.items():
        target = base / rel
        if content is None:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)


def make_fake_context(
    *,
    runner: FakeProcessRunner | None = None,
    interactive: bool = False,
    home: Path | None = None,
    launcher: FakeSessionLauncher | None = None,
    dotfiles_dir: Path | None = None,
    mask_provider: FakeMaskProvider | None = None,
    settings: Settings | None = None,
) -> AppContext:
    """Build an AppContext backed by fakes for CLI tests."""
    home_path = home or Path("/home/evan")
    provider = mask_provider or FakeMaskProvider()
    return AppContext(
        runner=runner or FakeProcessRunner(),
        settings=settings or Settings(),
        interactive=interactive,
        home=home_path,
        launcher=launcher or FakeSessionLauncher(),
        mask_provider_factory=lambda _account: provider,
        dotfiles_dir=dotfiles_dir or Path("/home/evan/dotfiles"),
    )
