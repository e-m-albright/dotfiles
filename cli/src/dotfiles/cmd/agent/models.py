"""Domain models for agent setup: the overview dashboard and skill-health verify."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import Agent
from dotfiles.cmd.agent.capability_matrix import CapabilityRow


class AgentPresenceRow(BaseModel):
    """One matrix row: a label plus per-vendor bool cells (MCP, hooks, subagents, …)."""

    model_config = ConfigDict(frozen=True)

    label: str
    cells: dict[str, bool]  # keyed by agent name


class PluginRow(BaseModel):
    """One installed Claude Code plugin (from installed_plugins.json)."""

    model_config = ConfigDict(frozen=True)

    name: str
    marketplace: str
    version: str
    declared: bool = True  # listed in plugins.yaml (our allowlist) vs drift


class ValueRow(BaseModel):
    """One labelled row whose per-agent cells hold display text (e.g. counts)."""

    model_config = ConfigDict(frozen=True)

    label: str
    cells: dict[str, str]  # keyed by agent name


class SkillsSummary(BaseModel):
    """Skill counts in the agent overview."""

    model_config = ConfigDict(frozen=True)

    canonical_skills: int
    claude_deployed: int
    cursor_deployed: int
    shared_deployed: int


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
    source_path: str = ""  # absolute path of the config, for a clickable link


AgentSurfaceStatus = Literal["present", "empty", "missing", "skipped"]


class AgentSurface(BaseModel):
    """One path check within a agent surface report."""

    model_config = ConfigDict(frozen=True)

    agent: Agent
    label: str
    status: AgentSurfaceStatus
    detail: str = ""
    quantity: str = ""  # the "how much/what" cell, e.g. "53 skills" or "key-only"
    path: str = ""  # absolute path, for a clickable link (empty when not file-backed)


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


CoverageState = Literal["active", "gap", "local", "na"]


class UniformityRow(BaseModel):
    """One enforced-tier capability across vendors, classified by deployment.

    Cross-references vendor SUPPORT (the capability matrix) with our live
    DEPLOYMENT, splitting gaps into closable vs not:
    - ``active`` — supported and deployed (or native to the vendor).
    - ``gap`` — supported, not deployed, and CLOSABLE by a global deploy.
    - ``local`` — supported but only at a scope we don't globally control
      (workspace-local config, an extension, or a beta with no stable API) —
      a real gap, but not one a global dotfiles deploy can close.
    - ``na`` — the vendor doesn't support it.
    """

    model_config = ConfigDict(frozen=True)

    capability: str
    cells: dict[str, CoverageState]  # keyed by agent name


class AgentOverview(BaseModel):
    """Complete snapshot of the agentic setup, from AgentOverviewService.overview()."""

    model_config = ConfigDict(frozen=True)

    mcp: tuple[AgentPresenceRow, ...]
    hooks: tuple[AgentPresenceRow, ...]
    skills: SkillsSummary
    agents: tuple[AgentPresenceRow, ...]
    rules: RulesSummary
    permissions: tuple[PermissionRow, ...]
    vendor_surfaces: tuple[AgentSurface, ...] = ()
    plugins: tuple[PluginRow, ...] = ()
    skills_rules: tuple[ValueRow, ...] = ()
    capabilities: tuple[CapabilityRow, ...] = ()
    uniformity: tuple[UniformityRow, ...] = ()
    fleet_doc_stale_days: int | None = None


class CatechismEntry(BaseModel):
    """One call-and-response of the code-health Catechism: a symptom → the rite to reach for."""

    model_config = ConfigDict(frozen=True)

    symptom: str  # what you want (the question)
    rite: str  # the skill/command to reach for (the answer)
    tier: str  # where it sits in the ontology


class LanguagePack(BaseModel):
    """Per-language code-health config — selected by marker files at bootstrap.

    `suppression_patterns` + `files_glob` drive the ratchet; `tools` is reference
    only (the canonical per-language gate commands), not consumed by the ratchet.
    """

    model_config = ConfigDict(frozen=True)

    language: str
    markers: tuple[str, ...] = ()
    files_glob: str
    run_from: str = "."
    suppression_patterns: dict[str, str]
    tools: dict[str, str] = {}


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
    language: str = "generic"  # the detected language pack (or "generic" fallback)
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
