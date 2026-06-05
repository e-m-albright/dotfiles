"""Associate live agent processes with the zellij session each runs in.

A coding agent (Claude Code, Codex) launched inside a zellij pane inherits that
pane's ``ZELLIJ_SESSION_NAME`` in its environment — so the session an agent
belongs to is read straight from the process, not guessed from its working
directory (two sessions can share a cwd; a directory is not an identity). The
Sessions pane uses this to show live agent work next to each session.

Read-only over the ProcessRunner port: ``pgrep -x <agent>`` to find the live
processes, then ``ps eww`` to read each one's environment.
"""

from __future__ import annotations

import re

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.agent import Agent
from dotfiles.cmd.session.models import AgentActivity

# Coding agents we look for, keyed by their exact process ``comm`` (== Agent value).
_AGENT_COMMS: tuple[Agent, ...] = ("claude", "codex")

# Pulled from the process environment that ``ps eww`` appends to the command.
# Session names carry no whitespace, so ``\S+`` captures the whole value.
_SESSION_RE = re.compile(r"\bZELLIJ_SESSION_NAME=(\S+)")
_PWD_RE = re.compile(r"\bPWD=(\S+)")


def _pids(runner: ProcessRunner, comm: str) -> list[int]:
    """PIDs of running processes named exactly *comm* (pgrep exits 1 = none)."""
    result = runner.run(("pgrep", "-x", comm))
    return [int(token) for token in result.stdout.split() if token.isdigit()]


def _activity(runner: ProcessRunner, agent: Agent, pid: int) -> AgentActivity:
    """Read *pid*'s zellij session and cwd from its environment."""
    result = runner.run(("ps", "eww", "-p", str(pid), "-o", "command="))
    text = result.stdout if result.ok else ""
    session = _SESSION_RE.search(text)
    pwd = _PWD_RE.search(text)
    return AgentActivity(
        agent=agent,
        session=session.group(1) if session else None,
        cwd=pwd.group(1) if pwd else "",
    )


def live_agents(runner: ProcessRunner) -> list[AgentActivity]:
    """Every running Claude/Codex process, with the zellij session it lives in."""
    return [_activity(runner, agent, pid) for agent in _AGENT_COMMS for pid in _pids(runner, agent)]


def agents_by_session(
    agents: list[AgentActivity],
) -> tuple[dict[str, list[AgentActivity]], list[AgentActivity]]:
    """Group agents by their zellij session; those with no session are "elsewhere"."""
    matched: dict[str, list[AgentActivity]] = {}
    unmatched: list[AgentActivity] = []
    for agent in agents:
        if agent.session is None:
            unmatched.append(agent)
        else:
            matched.setdefault(agent.session, []).append(agent)
    return matched, unmatched
