#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_logging.py
Tests for logging_config: _parse_level, set/enable/disable, is_xwchat_logging_enabled.
"""

from __future__ import annotations

import logging
import os

import pytest

from exonware.xwchat.logging_config import (
    set_xwchat_log_level,
    enable_xwchat_logging,
    disable_xwchat_logging,
    is_xwchat_logging_enabled,
    _parse_level,
    apply_xwchat_logging_from_env,
)


def test_parse_level_empty() -> None:
    assert _parse_level("") is None
    assert _parse_level("   ") is None


def test_parse_level_names() -> None:
    assert _parse_level("DEBUG") == logging.DEBUG
    assert _parse_level("INFO") == logging.INFO
    assert _parse_level("WARNING") == logging.WARNING
    assert _parse_level("ERROR") == logging.ERROR


def test_parse_level_disable() -> None:
    assert _parse_level("0") == logging.CRITICAL
    assert _parse_level("OFF") == logging.CRITICAL
    assert _parse_level("DISABLED") == logging.CRITICAL
    assert _parse_level("FALSE") == logging.CRITICAL
    assert _parse_level("NONE") == logging.CRITICAL


def test_parse_level_unknown_returns_none() -> None:
    assert _parse_level("UNKNOWN") is None


def test_set_xwchat_log_level_int() -> None:
    set_xwchat_log_level(logging.DEBUG)
    assert not _xwchat_logger_disabled()
    set_xwchat_log_level(logging.INFO)


def test_set_xwchat_log_level_str() -> None:
    set_xwchat_log_level("WARNING")
    assert not _xwchat_logger_disabled()
    set_xwchat_log_level("INFO")


def test_enable_xwchat_logging() -> None:
    enable_xwchat_logging(logging.INFO)
    assert is_xwchat_logging_enabled() is True
    enable_xwchat_logging("DEBUG")
    assert is_xwchat_logging_enabled() is True


def test_disable_xwchat_logging() -> None:
    disable_xwchat_logging()
    assert is_xwchat_logging_enabled() is False
    enable_xwchat_logging()


def test_is_xwchat_logging_enabled_after_enable() -> None:
    enable_xwchat_logging()
    assert is_xwchat_logging_enabled() is True


def test_apply_xwchat_logging_from_env_idempotent() -> None:
    apply_xwchat_logging_from_env()
    apply_xwchat_logging_from_env()
    # Should not raise; second call is no-op (global _APPLIED)


def _xwchat_logger_disabled() -> bool:
    from exonware.xwchat.logging_config import _xwchat_logger
    return _xwchat_logger().disabled
