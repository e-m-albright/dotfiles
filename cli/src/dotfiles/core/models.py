"""Domain models. All immutable pydantic models, returned by the core layer."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Agent overview models
# ---------------------------------------------------------------------------


class McpRow(BaseModel):
    """One MCP server row in the agent overview."""

    model_config = ConfigDict(frozen=True)

    server: str
    claude: bool
    cursor: bool
    codex: bool
    gemini: bool


class HookRow(BaseModel):
    """One hook-event row in the agent overview."""

    model_config = ConfigDict(frozen=True)

    event: str
    claude: bool
    cursor: bool
    codex: bool


class SkillsSummary(BaseModel):
    """Skill counts in the agent overview."""

    model_config = ConfigDict(frozen=True)

    canonical_skills: int
    claude_deployed: int
    shared_deployed: int


class AgentRow(BaseModel):
    """One subagent row in the agent overview."""

    model_config = ConfigDict(frozen=True)

    name: str
    claude: bool
    codex: bool
    pi: bool


class RulesSummary(BaseModel):
    """Rule counts in the agent overview."""

    model_config = ConfigDict(frozen=True)

    canonical_rules: int
    claude_deployed: int
    cursor_deployed: int


class PermissionRow(BaseModel):
    """One permission-source row in the agent overview."""

    model_config = ConfigDict(frozen=True)

    label: str
    allow: int
    deny: int
    # For codex default.rules, deny=0 and allow holds prefix_rule count.
    # prefix_rules is a convenience alias — callers use it for codex rows.
    prefix_rules: int = 0


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


class GeminiChunk(BaseModel):
    """One chunk from the Gemini advisor prompt, sized to fit saved-info entries."""

    model_config = ConfigDict(frozen=True)

    name: str
    char_count: int
    content: str


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


class AgentOverview(BaseModel):
    """Complete snapshot of the agentic setup, from AgentOverviewService.overview()."""

    model_config = ConfigDict(frozen=True)

    mcp: tuple[McpRow, ...]
    hooks: tuple[HookRow, ...]
    skills: SkillsSummary
    agents: tuple[AgentRow, ...]
    rules: RulesSummary
    permissions: tuple[PermissionRow, ...]
    vendor_surfaces: tuple[VendorSurface, ...] = ()


# ---------------------------------------------------------------------------
# Ledger + fleet models
# ---------------------------------------------------------------------------


class LedgerEntry(BaseModel):
    """One agent-activity record. Written by the hot-path hook, read by fleet."""

    model_config = ConfigDict(frozen=True)

    ts: datetime
    session_id: str
    vendor: str
    cwd: str
    branch: str | None = None
    task: str | None = None
    status: str


class FleetSession(BaseModel):
    """One live agent session discovered by fleet (passive + ledger overlay)."""

    model_config = ConfigDict(frozen=True)

    vendor: str
    session_id: str | None
    cwd: str
    branch: str | None
    worktree: str | None
    last_active: datetime
    task: str | None
    source: str  # "transcript" | "ledger" | "both"


# ---------------------------------------------------------------------------
# Snapshot / drift models
# ---------------------------------------------------------------------------


class BrewState(BaseModel):
    """Installed Homebrew top-level packages at capture time."""

    model_config = ConfigDict(frozen=True)

    leaves: tuple[str, ...]
    casks: tuple[str, ...]


class SymlinkState(BaseModel):
    """One managed symlink and where it points at capture time."""

    model_config = ConfigDict(frozen=True)

    path: str
    target: str
    ok: bool


class Snapshot(BaseModel):
    """A point-in-time capture of machine state, persisted as JSON."""

    model_config = ConfigDict(frozen=True)

    taken_at: datetime
    brew: BrewState
    runtimes: dict[str, str]
    symlinks: tuple[SymlinkState, ...]
    agent_config: dict[str, str]


class RuntimeChange(BaseModel):
    """A runtime whose version differs between two snapshots."""

    model_config = ConfigDict(frozen=True)

    name: str
    old: str
    new: str


class SymlinkChange(BaseModel):
    """A managed symlink whose target or ok-state differs between two snapshots."""

    model_config = ConfigDict(frozen=True)

    path: str
    old_target: str
    new_target: str
    broke: bool


class SnapshotDiff(BaseModel):
    """The drift between two snapshots (old -> new)."""

    model_config = ConfigDict(frozen=True)

    brew_added: tuple[str, ...]
    brew_removed: tuple[str, ...]
    runtimes_changed: tuple[RuntimeChange, ...]
    symlinks_changed: tuple[SymlinkChange, ...]
    agent_config_changed: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (
            self.brew_added
            or self.brew_removed
            or self.runtimes_changed
            or self.symlinks_changed
            or self.agent_config_changed
        )
