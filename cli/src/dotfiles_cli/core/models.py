"""Domain models. All immutable pydantic models, returned by the core layer."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CommandResult(BaseModel):
    """Result of running an external command via a ProcessRunner port."""

    model_config = ConfigDict(frozen=True)

    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


StepLevel = Literal["success", "info", "warn", "error"]


class StepResult(BaseModel):
    """One reported step of a remote action, rendered by the CLI/TUI."""

    model_config = ConfigDict(frozen=True)

    level: StepLevel
    message: str


class RemoteStatus(BaseModel):
    """Snapshot of the Mac's remote-shell entrypoint state."""

    model_config = ConfigDict(frozen=True)

    remote_login_on: bool
    tailscale_connected: bool
    tailnet_ip: str | None
    host: str
    user: str
    mosh_server: str


class ConnectionInfo(BaseModel):
    """Everything needed to connect from Termius."""

    model_config = ConfigDict(frozen=True)

    user: str
    host: str
    session: str
    mosh_server: str
    tailnet_ip: str | None

    @property
    def startup_command(
        self,
    ) -> str:  # keep in sync with the other zellij attach-command representation
        return f"zellij attach --create {self.session}"

    @property
    def mosh_command(self) -> str:
        return f"mosh --server={self.mosh_server} {self.user}@{self.host} -- {self.startup_command}"


class Session(BaseModel):
    """A zellij session as reported by `zellij list-sessions`."""

    model_config = ConfigDict(frozen=True)

    name: str
    running: bool
    current: bool


CheckStatus = Literal["ok", "missing", "warn", "fixed"]


class CheckResult(BaseModel):
    """One row of `dotfiles doctor` output."""

    model_config = ConfigDict(frozen=True)

    section: str
    name: str
    status: CheckStatus
    detail: str = ""
    hint: str = ""

    @property
    def is_failure(self) -> bool:
        return self.status == "missing"


VendorSurfaceStatus = Literal["present", "empty", "missing", "skipped"]


class VendorSurface(BaseModel):
    """One path check within a vendor surface report."""

    model_config = ConfigDict(frozen=True)

    vendor: str
    label: str
    status: VendorSurfaceStatus
    detail: str = ""


FileValidationStatus = Literal["ok", "warn", "fail"]


class FileValidation(BaseModel):
    """Result of validating one skill or agent markdown file."""

    model_config = ConfigDict(frozen=True)

    rel_path: str
    kind: str  # "skill" or "agent"
    status: FileValidationStatus
    body_lines: int = 0
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


ThroughputTier = Literal["autocomplete-grade", "interactive-grade", "tolerable", "painful"]


class BenchResult(BaseModel):
    """Metrics from a single LM Studio bench run."""

    model_config = ConfigDict(frozen=True)

    model: str
    tg_tps: float
    pp_tps: float
    pp_tokens: int
    pp_wall: float
    ttft: float
    reasoning_tokens: int
    content_len: int

    @property
    def tier(self) -> ThroughputTier:
        """Classify token-gen throughput, matching llm-bench.sh classify()."""
        if self.tg_tps >= 100:
            return "autocomplete-grade"
        if self.tg_tps >= 40:
            return "interactive-grade"
        if self.tg_tps >= 20:
            return "tolerable"
        return "painful"
