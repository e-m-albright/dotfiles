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


class CatechismEntry(BaseModel):
    """One call-and-response of the code-health Catechism: a symptom → the rite to reach for."""

    model_config = ConfigDict(frozen=True)

    symptom: str  # what you want (the question)
    rite: str  # the skill/command to reach for (the answer)
    tier: str  # where it sits in the ontology


class Hotspot(BaseModel):
    """One churn*LOC hotspot from scorecard.sh — where refactor effort pays."""

    model_config = ConfigDict(frozen=True)

    file: str
    score: int
    churn: int
    loc: int


class Scorecard(BaseModel):
    """Parsed `scorecard.sh --json` output: the deterministic metric set."""

    model_config = ConfigDict(frozen=True)

    loc: int
    since: str
    suppressions: dict[str, int]
    hotspots: tuple[Hotspot, ...] = ()


class HealthBootstrap(BaseModel):
    """Result of `dotfiles agent health`: a scope's seeded code-health backbone."""

    model_config = ConfigDict(frozen=True)

    scope: str
    target: str
    baselines_path: str
    findings_path: str
    created: bool  # False when baselines already existed and were kept
    scorecard: Scorecard
    total_suppressions: int


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
