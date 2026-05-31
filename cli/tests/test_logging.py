import logging

from dotfiles_cli.core.logging import configure_logging, get_logger


def test_configure_sets_level(caplog) -> None:
    configure_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_logger_emits_structured_event(caplog) -> None:
    configure_logging("INFO")
    log = get_logger("test")
    with caplog.at_level(logging.INFO):
        log.info("remote_action", action="toggle", target="remote_login")
    assert "remote_action" in caplog.text
    assert "toggle" in caplog.text


def test_reconfigure_to_lower_level_takes_effect() -> None:
    configure_logging("ERROR")
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG
