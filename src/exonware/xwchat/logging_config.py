#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/logging_config.py
XWChat logging configuration using xwsystem logging.
Provides enable/disable and log level control for xwchat (env and API).
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.4
"""

from __future__ import annotations

import logging
import os

# Reuse xwsystem logging: all xwchat loggers are under "exonware.xwchat"
from exonware.xwsystem import get_logger

XWCHAT_LOGGER_NAME = "exonware.xwchat"

# Env keys (case-insensitive for enabled; level: DEBUG, INFO, WARNING, ERROR, 0/off)
_ENV_XWCHAT_LOGGING_ENABLED = "XWCHAT_LOGGING_ENABLED"
_ENV_XWCHAT_LOG_LEVEL = "XWCHAT_LOG_LEVEL"

_LEVEL_NAMES = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
_APPLIED = False


def _xwchat_logger() -> logging.Logger:
    """Return the xwchat root logger (reuses xwsystem hierarchy)."""
    return get_logger(XWCHAT_LOGGER_NAME)


def _parse_level(value: str) -> int | None:
    """Parse level from env: DEBUG, INFO, WARNING, ERROR, or 0/off/disabled/false."""
    if not value:
        return None
    v = value.strip().upper()
    if v in ("0", "OFF", "DISABLED", "FALSE", "NONE"):
        return logging.CRITICAL  # effectively disable
    return _LEVEL_NAMES.get(v)


def apply_xwchat_logging_from_env() -> None:
    """
    Configure xwchat logging from environment (called on package import).
    - XWCHAT_LOGGING_ENABLED=false|0 → disable xwchat logs
    - XWCHAT_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|0 → set level for exonware.xwchat
    Respects xwsystem: if XSYSTEM_LOGGING_DISABLE=true, xwsystem get_logger already returns disabled loggers.
    """
    global _APPLIED
    if _APPLIED:
        return
    _APPLIED = True
    logger = _xwchat_logger()
    enabled = os.environ.get(_ENV_XWCHAT_LOGGING_ENABLED, "").strip().lower()
    if enabled in ("false", "0", "no", "off", "disabled"):
        logger.setLevel(logging.CRITICAL)
        logger.disabled = True
        return
    level_str = os.environ.get(_ENV_XWCHAT_LOG_LEVEL, "").strip()
    if level_str:
        level = _parse_level(level_str)
        if level is not None:
            logger.disabled = False
            logger.setLevel(level)


def set_xwchat_log_level(level: int | str) -> None:
    """
    Set log level for all xwchat loggers (exonware.xwchat and children).
    level: logging constant (e.g. logging.INFO) or name "DEBUG","INFO","WARNING","ERROR".
    """
    logger = _xwchat_logger()
    if isinstance(level, str):
        level = _LEVEL_NAMES.get(level.strip().upper(), logging.INFO)
    logger.setLevel(level)
    logger.disabled = False


def enable_xwchat_logging(level: int | str = logging.INFO) -> None:
    """Enable xwchat logging and set level (default INFO)."""
    logger = _xwchat_logger()
    logger.disabled = False
    if isinstance(level, str):
        level = _LEVEL_NAMES.get(level.strip().upper(), logging.INFO)
    logger.setLevel(level)


def disable_xwchat_logging() -> None:
    """Disable xwchat logging (set to CRITICAL and mark disabled)."""
    logger = _xwchat_logger()
    logger.setLevel(logging.CRITICAL)
    logger.disabled = True


def is_xwchat_logging_enabled() -> bool:
    """Return True if xwchat logger is not disabled."""
    return not _xwchat_logger().disabled
