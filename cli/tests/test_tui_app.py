"""Mission Control TUI app boots and mounts panes."""

import pytest

from dotfiles.tui.app import MissionControlApp
from tests.fakes import make_fake_context


@pytest.mark.asyncio
async def test_app_boots_with_injected_context():
    app = MissionControlApp(ctx=make_fake_context())
    async with app.run_test() as pilot:
        await pilot.pause()
        # Title bar renders the brand; app is running.
        assert "MISSION CONTROL" in app.title.upper()
        assert app.is_running
