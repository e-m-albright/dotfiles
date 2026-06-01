"""Guard that silent-degradation paths actually emit a log line.

These branches used to swallow failures invisibly (structlog was configured but
never called). If someone removes the logging, these tests fail — keeping the
observability honest rather than decorative.
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotfiles.core.agent_config import load_config, load_mcp_servers
from dotfiles.core.logging import configure_logging
from dotfiles.core.scaffold.tool_registry import load_registry


def test_malformed_mcp_config_logs_warning(tmp_path: Path, caplog: object) -> None:
    configure_logging("DEBUG")
    bad = tmp_path / "mcp-servers.json"
    bad.write_text("{ not valid json")
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        result = load_mcp_servers(bad)
    assert result == {}
    assert any("mcp_servers_read_failed" in r.getMessage() for r in caplog.records)  # type: ignore[attr-defined]


def test_malformed_registry_logs_warning(tmp_path: Path, caplog: object) -> None:
    configure_logging("DEBUG")
    (tmp_path / "agents" / "shared").mkdir(parents=True)
    (tmp_path / "agents" / "shared" / "tool-targets.json").write_text("{ broken")
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        result = load_registry(tmp_path)
    assert result == {}
    assert any("tool_registry_load_failed" in r.getMessage() for r in caplog.records)  # type: ignore[attr-defined]


def test_invalid_config_logs_warning(tmp_path: Path, caplog: object) -> None:
    from pydantic import BaseModel

    class _Model(BaseModel):
        required: int

    bad = tmp_path / "config.json"
    bad.write_text('{"required": "not-an-int"}')
    configure_logging("DEBUG")
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        result = load_config(bad, _Model)
    assert result is None
    assert any("config_parse_failed" in r.getMessage() for r in caplog.records)  # type: ignore[attr-defined]
