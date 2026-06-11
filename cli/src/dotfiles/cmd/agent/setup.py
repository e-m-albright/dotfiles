"""Orchestrate `agent setup` — pick Agents, run each vendor's setup, collect results.

The per-Agent vendor dispatch lives here as data (not an if/elif chain in the
Typer handler), and `run_setup` returns the step results per Agent as a list the
CLI renders. Selection, dispatch, and failure aggregation are therefore unit-
testable without the Typer runner: pass a fake `dispatch` to exercise
partial-failure / ordering without running real vendor setups.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from dotfiles.app.context import AppContext
from dotfiles.cmd.agent.vendors.claude import setup_claude
from dotfiles.cmd.agent.vendors.codex import setup_codex
from dotfiles.cmd.agent.vendors.cursor import setup_cursor
from dotfiles.cmd.agent.vendors.gemini import setup_gemini
from dotfiles.cmd.agent.vendors.hermes import setup_hermes
from dotfiles.cmd.agent.vendors.pi import setup_pi
from dotfiles.console import has_errors
from dotfiles.result import StepResult

# One Agent's setup, normalized to a uniform call: each adapter takes the shared
# AppContext plus both flags and ignores whichever it doesn't accept.
VendorSetup = Callable[[AppContext, bool, bool], list[StepResult]]


def _claude(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_claude(
        runner=ctx.runner,
        home=ctx.home,
        dotfiles_dir=ctx.dotfiles_dir,
        clean=clean,
        reset_mcp=reset_mcp,
    )


def _cursor(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_cursor(
        runner=ctx.runner, home=ctx.home, dotfiles_dir=ctx.dotfiles_dir, reset_mcp=reset_mcp
    )


def _codex(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_codex(runner=ctx.runner, home=ctx.home, dotfiles_dir=ctx.dotfiles_dir)


def _gemini(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_gemini(
        runner=ctx.runner, home=ctx.home, dotfiles_dir=ctx.dotfiles_dir, reset_mcp=reset_mcp
    )


def _pi(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_pi(runner=ctx.runner, home=ctx.home, dotfiles_dir=ctx.dotfiles_dir)


def _hermes(ctx: AppContext, clean: bool, reset_mcp: bool) -> list[StepResult]:
    return setup_hermes(runner=ctx.runner, home=ctx.home, dotfiles_dir=ctx.dotfiles_dir)


# Dispatch as data — order is the setup order (claude → … → pi → hermes).
VENDOR_SETUP: Mapping[str, VendorSetup] = {
    "claude": _claude,
    "cursor": _cursor,
    "codex": _codex,
    "gemini": _gemini,
    "pi": _pi,
    "hermes": _hermes,
}

# The Agents `setup` runs when none is named, in dispatch order.
ALL_AGENTS: tuple[str, ...] = tuple(VENDOR_SETUP)


@dataclass(frozen=True)
class AgentSetupResult:
    """One Agent's setup outcome: its name and the steps it produced."""

    agent: str
    steps: list[StepResult]

    @property
    def failed(self) -> bool:
        return has_errors(self.steps)


def run_setup(
    app_ctx: AppContext,
    *,
    agents: Sequence[str],
    clean: bool,
    reset_mcp: bool,
    dispatch: Mapping[str, VendorSetup] = VENDOR_SETUP,
) -> list[AgentSetupResult]:
    """Run setup for each named Agent in order, collecting per-Agent step results.

    `dispatch` defaults to the real vendor setups; tests inject a fake to exercise
    selection and failure aggregation without touching the filesystem.
    """
    return [
        AgentSetupResult(agent=name, steps=dispatch[name](app_ctx, clean, reset_mcp))
        for name in agents
    ]
