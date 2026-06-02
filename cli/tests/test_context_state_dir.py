"""state_dir resolution in the composition root."""

from dotfiles.app.context import build_real_context


def test_state_dir_defaults_under_local_state(monkeypatch):
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    ctx = build_real_context(interactive=False)
    assert ctx.state_dir == ctx.home / ".local" / "state" / "dotfiles"


def test_state_dir_honors_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    ctx = build_real_context(interactive=False)
    assert ctx.state_dir == tmp_path / "dotfiles"
