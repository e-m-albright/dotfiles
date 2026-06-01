from dotfiles_cli.core.models import Session
from dotfiles_cli.core.sessions import parse_sessions


def test_parse_empty() -> None:
    assert parse_sessions("No active zellij sessions found.\n") == []
    assert parse_sessions("") == []


def test_parse_running_current_and_exited() -> None:
    out = (
        "mobile [Created 1h 30m ago]\n"
        "work [Created 5m ago] (current)\n"
        "old [Created 2d ago] (EXITED - attach to resurrect)\n"
    )
    sessions = parse_sessions(out)
    assert sessions == [
        Session(name="mobile", running=True, current=False),
        Session(name="work", running=True, current=True),
        Session(name="old", running=False, current=False),
    ]
