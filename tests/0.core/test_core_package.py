#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_package.py
Tests for package __init__: version exports, logging exports, all public API.
"""

from __future__ import annotations

import pytest


def test_package_version_exports() -> None:
    from exonware.xwchat import __version__, __author__, __email__
    assert __version__
    assert __author__
    assert __email__


def test_package_logging_exports() -> None:
    from exonware.xwchat import (
        set_xwchat_log_level,
        enable_xwchat_logging,
        disable_xwchat_logging,
        is_xwchat_logging_enabled,
    )
    assert callable(set_xwchat_log_level)
    assert callable(enable_xwchat_logging)
    assert callable(disable_xwchat_logging)
    assert callable(is_xwchat_logging_enabled)


def test_package_get_logger() -> None:
    from exonware.xwchat import get_logger
    log = get_logger("exonware.xwchat.test")
    assert log is not None


def test_package_agent_and_base() -> None:
    from exonware.xwchat import XWChatAgent, AChatAgent, AChatProvider
    assert XWChatAgent is not None
    assert AChatAgent is not None
    assert AChatProvider is not None


def test_package_defs_exports() -> None:
    from exonware.xwchat import ChatCapability, ChatProviderType, MessageContext, ChatMessageType
    assert ChatCapability is not None
    assert ChatProviderType is not None
    assert MessageContext is not None
    assert ChatMessageType is not None


def test_package_errors_exports() -> None:
    from exonware.xwchat import (
        XWChatError,
        XWChatAgentError,
        XWChatProviderError,
        XWChatMessageError,
        XWChatConnectionError,
    )
    assert XWChatError is not None
    assert XWChatAgentError is not None
    assert XWChatProviderError is not None
    assert XWChatMessageError is not None
    assert XWChatConnectionError is not None
