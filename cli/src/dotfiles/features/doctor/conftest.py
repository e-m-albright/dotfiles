"""Keep optional private integration discovery independent of the host environment."""

import pytest


@pytest.fixture(autouse=True)
def isolated_private_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRIVATE_AUTOMATION_ROOT", raising=False)
