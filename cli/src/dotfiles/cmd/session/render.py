"""Row fragments shared by the session CLI list and the Mission Control pane."""

from collections.abc import Sequence

from rich.markup import escape

from dotfiles.cmd.session.models import AgentActivity

# Brand-gold for "what's running" previews, in both the CLI and the TUI.
PROGRAM_STYLE = "#cdbf80"


def agent_badge(agents: Sequence[AgentActivity]) -> str:
    """Green badge of agent names active in a session, e.g. ``claude · codex``."""
    return " · ".join(f"[green]{a.agent}[/]" for a in agents)


def programs_preview(programs: Sequence[str], limit: int = 3) -> str:
    """Brand-gold summary of running pane titles, capped with a ``+N`` overflow.

    Titles are escaped so a stray ``[`` in a pane title can't be read as markup.
    """
    shown = [escape(p) for p in programs[:limit]]
    if len(programs) > limit:
        shown.append(f"+{len(programs) - limit}")
    return f"[{PROGRAM_STYLE}]" + " · ".join(shown) + "[/]"
