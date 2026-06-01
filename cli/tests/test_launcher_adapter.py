from dotfiles_cli.adapters.launcher import FzfExecLauncher
from dotfiles_cli.core.sessions import SessionLauncher


def test_launcher_satisfies_port() -> None:
    assert isinstance(FzfExecLauncher(), SessionLauncher)


def test_pick_returns_none_for_empty_options() -> None:
    # No fzf is spawned when there's nothing to pick.
    assert FzfExecLauncher().pick([]) is None


def test_pick_parses_fzf_stdout(monkeypatch) -> None:
    import subprocess

    class _Done:
        stdout = "work\n"
        returncode = 0

    def fake_run(*_args, **_kwargs):
        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert FzfExecLauncher().pick(["mobile", "work"]) == "work"


def test_pick_returns_none_when_fzf_cancelled(monkeypatch) -> None:
    import subprocess

    class _Cancelled:
        stdout = ""
        returncode = 130  # fzf exit code on Esc/Ctrl-C

    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: _Cancelled())
    assert FzfExecLauncher().pick(["mobile"]) is None


def test_attach_rejects_empty_command() -> None:
    import pytest

    with pytest.raises(ValueError, match="non-empty"):
        FzfExecLauncher().attach([])
