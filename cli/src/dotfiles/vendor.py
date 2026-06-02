"""The canonical typed identifiers for every AI tool we configure."""

from typing import Literal

Vendor = Literal["claude", "cursor", "codex", "gemini", "pi"]
VENDORS: tuple[Vendor, ...] = ("claude", "cursor", "codex", "gemini", "pi")
# The vendors the agent-overview dashboard tracks (its row models carry no `pi`
# column). snapshot and skill-health both iterate exactly this set.
OVERVIEW_VENDORS: tuple[Vendor, ...] = ("claude", "cursor", "codex", "gemini")
