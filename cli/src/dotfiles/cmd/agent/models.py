"""Domain models for agent setup: the overview dashboard and skill-health verify."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import Agent


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


class SubagentRow(BaseModel):
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
    prefix_rules: int = 0


AgentSurfaceStatus = Literal["present", "empty", "missing", "skipped"]


class AgentSurface(BaseModel):
    """One path check within a agent surface report."""

    model_config = ConfigDict(frozen=True)

    agent: Agent
    label: str
    status: AgentSurfaceStatus
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
    """One chunk of the web-chat advisor prompt, sized to fit saved-info entries."""

    model_config = ConfigDict(frozen=True)

    name: str
    char_count: int
    content: str


class AgentOverview(BaseModel):
    """Complete snapshot of the agentic setup, from AgentOverviewService.overview()."""

    model_config = ConfigDict(frozen=True)

    mcp: tuple[McpRow, ...]
    hooks: tuple[HookRow, ...]
    skills: SkillsSummary
    agents: tuple[SubagentRow, ...]
    rules: RulesSummary
    permissions: tuple[PermissionRow, ...]
    vendor_surfaces: tuple[AgentSurface, ...] = ()


class McpProbe(BaseModel):
    """Result of probing one MCP server's reachability."""

    model_config = ConfigDict(frozen=True)

    server: str
    ok: bool
    detail: str


class AgentVerify(BaseModel):
    """Per-agent skill-health: deployment counts, drift, and MCP probes."""

    model_config = ConfigDict(frozen=True)

    agent: Agent
    skills_deployed: int
    skills_expected: int
    agents_deployed: int
    agents_expected: int
    drift: tuple[str, ...]
    mcp: tuple[McpProbe, ...]
