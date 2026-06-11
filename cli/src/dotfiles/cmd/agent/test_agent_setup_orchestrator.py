"""Selection + dispatch + failure aggregation for `agent setup`, sans Typer."""

from __future__ import annotations

from dotfiles.cmd.agent.setup import ALL_AGENTS, VENDOR_SETUP, AgentSetupResult, run_setup
from dotfiles.result import StepResult
from dotfiles.testing.fakes import make_fake_context


def _ok(agent: str) -> StepResult:
    return StepResult(level="success", message=f"{agent} ok")


def _fail(agent: str) -> StepResult:
    return StepResult(level="error", message=f"{agent} boom")


def test_all_agents_matches_dispatch_order() -> None:
    # The no-argument run covers every dispatchable Agent, in dispatch order.
    assert ALL_AGENTS == ("claude", "cursor", "codex", "gemini", "pi", "hermes")
    assert tuple(VENDOR_SETUP) == ALL_AGENTS


def test_run_setup_runs_only_named_agents_in_order() -> None:
    ctx = make_fake_context()
    calls: list[str] = []
    dispatch = {
        name: (lambda _c, _cl, _r, n=name: (calls.append(n), [_ok(n)])[1]) for name in ALL_AGENTS
    }

    results = run_setup(
        ctx, agents=["codex", "claude"], clean=False, reset_mcp=False, dispatch=dispatch
    )

    assert calls == ["codex", "claude"]
    assert [r.agent for r in results] == ["codex", "claude"]


def test_run_setup_aggregates_partial_failure() -> None:
    ctx = make_fake_context()
    dispatch = {
        "claude": lambda _c, _cl, _r: [_fail("claude")],
        "codex": lambda _c, _cl, _r: [_ok("codex")],
    }

    results = run_setup(
        ctx, agents=["claude", "codex"], clean=False, reset_mcp=False, dispatch=dispatch
    )

    by_agent = {r.agent: r for r in results}
    assert by_agent["claude"].failed
    assert not by_agent["codex"].failed


def test_run_setup_forwards_flags_to_dispatch() -> None:
    ctx = make_fake_context()
    seen: dict[str, tuple[bool, bool]] = {}
    dispatch = {
        "claude": lambda _c, cl, r: (seen.__setitem__("claude", (cl, r)), [_ok("claude")])[1],
    }

    run_setup(ctx, agents=["claude"], clean=True, reset_mcp=True, dispatch=dispatch)

    assert seen["claude"] == (True, True)


def test_agent_setup_result_failed_reflects_steps() -> None:
    assert AgentSetupResult("x", [_ok("x")]).failed is False
    assert AgentSetupResult("x", [_ok("x"), _fail("x")]).failed is True
