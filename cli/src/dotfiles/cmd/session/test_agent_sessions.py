"""Process-based agent discovery: session read from each agent's environment."""

from __future__ import annotations

from dotfiles.cmd.session.agent_sessions import agents_by_session, live_agents
from dotfiles.cmd.session.models import AgentActivity
from dotfiles.testing.fakes import FakeProcessRunner


def _env(*, session: str | None, pwd: str) -> str:
    """A `ps eww` command+env line carrying the given session/cwd."""
    parts = ["claude", "--settings", "/x.json", f"PWD={pwd}", "SHLVL=1"]
    if session is not None:
        parts.append(f"ZELLIJ_SESSION_NAME={session}")
    return " ".join(parts) + "\n"


def test_live_agents_reads_session_from_process_env() -> None:
    runner = FakeProcessRunner()
    runner.script(("pgrep", "-x", "claude"), stdout="14486\n21697\n")
    runner.script(
        ("ps", "eww", "-p", "14486", "-o", "command="),
        stdout=_env(session="people", pwd="/Users/dev/code/private/notes"),
    )
    runner.script(
        ("ps", "eww", "-p", "21697", "-o", "command="),
        stdout=_env(session="skills", pwd="/Users/dev/dotfiles"),
    )

    agents = live_agents(runner)

    assert [(a.agent, a.session) for a in agents] == [
        ("claude", "people"),
        ("claude", "skills"),
    ]


def test_live_agents_same_cwd_two_sessions_each_keep_their_own() -> None:
    # The collision that cwd-matching got wrong: two sessions at the same dir.
    runner = FakeProcessRunner()
    runner.script(("pgrep", "-x", "claude"), stdout="1\n2\n")
    runner.script(
        ("ps", "eww", "-p", "1", "-o", "command="),
        stdout=_env(session="dotfiles", pwd="/Users/dev/dotfiles"),
    )
    runner.script(
        ("ps", "eww", "-p", "2", "-o", "command="),
        stdout=_env(session="skills", pwd="/Users/dev/dotfiles"),
    )

    matched, unmatched = agents_by_session(live_agents(runner))

    assert set(matched) == {"dotfiles", "skills"}  # both, despite the shared cwd
    assert unmatched == []


def test_live_agents_no_session_env_is_unmatched() -> None:
    runner = FakeProcessRunner()
    runner.script(("pgrep", "-x", "claude"), stdout="7\n")
    runner.script(
        ("ps", "eww", "-p", "7", "-o", "command="),
        stdout=_env(session=None, pwd="/Users/dev/code/public"),
    )

    matched, unmatched = agents_by_session(live_agents(runner))

    assert matched == {}
    assert [(a.agent, a.cwd) for a in unmatched] == [("claude", "/Users/dev/code/public")]


def test_live_agents_empty_when_no_processes() -> None:
    # pgrep exits 1 with no output when nothing matches — that's just "none".
    runner = FakeProcessRunner()
    runner.script(("pgrep", "-x", "claude"), exit_code=1)
    runner.script(("pgrep", "-x", "codex"), exit_code=1)
    assert live_agents(runner) == []


def test_agents_by_session_groups_multiple_agents_per_session() -> None:
    agents = [
        AgentActivity(agent="claude", session="work", cwd="/w"),
        AgentActivity(agent="codex", session="work", cwd="/w"),
    ]
    matched, unmatched = agents_by_session(agents)
    assert [a.agent for a in matched["work"]] == ["claude", "codex"]
    assert unmatched == []
