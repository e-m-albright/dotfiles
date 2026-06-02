"""The canonical typed identifiers for every AI tool we configure."""

from typing import Literal

Agent = Literal["claude", "cursor", "codex", "gemini", "pi"]
AGENTS: tuple[Agent, ...] = ("claude", "cursor", "codex", "gemini", "pi")
# The vendors the agent-overview dashboard tracks (its row models carry no `pi`
# column). snapshot and skill-health both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = ("claude", "cursor", "codex", "gemini")
