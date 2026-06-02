"""Guard that silent-degradation paths actually emit a log line.

These branches used to swallow failures invisibly (structlog was configured but
never called). If someone removes the logging, these tests fail — keeping the
observability honest rather than decorative.
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotfiles.cmd.agent.config import load_config, load_mcp_servers
from dotfiles.logging import configure_logging


def test_malformed_mcp_config_logs_warning(tmp_path: Path, caplog: object) -> None:
    configure_logging("DEBUG")
    bad = tmp_path / "mcp-servers.json"
    bad.write_text("{ not valid json")
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        result = load_mcp_servers(bad)
    assert result == {}
    assert any("mcp_servers_read_failed" in r.getMessage() for r in caplog.records)  # type: ignore[attr-defined]


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
