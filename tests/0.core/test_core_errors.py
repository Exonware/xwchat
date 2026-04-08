#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_errors.py
Tests for error hierarchy: XWChatError, XWChatAgentError, XWChatProviderError,
XWChatMessageError, XWChatConnectionError.
"""

from __future__ import annotations

import pytest

from exonware.xwchat import (
    XWChatError,
    XWChatAgentError,
    XWChatProviderError,
    XWChatMessageError,
    XWChatConnectionError,
)


def test_xwchat_error_base() -> None:
    e = XWChatError("base")
    assert str(e) == "base"
    assert isinstance(e, Exception)


def test_xwchat_agent_error_inherits() -> None:
    e = XWChatAgentError("agent")
    assert isinstance(e, XWChatError)
    assert str(e) == "agent"


def test_xwchat_provider_error_inherits() -> None:
    e = XWChatProviderError("provider")
    assert isinstance(e, XWChatError)
    assert str(e) == "provider"


def test_xwchat_message_error_inherits() -> None:
    e = XWChatMessageError("message")
    assert isinstance(e, XWChatError)
    assert str(e) == "message"


def test_xwchat_connection_error_inherits_from_provider() -> None:
    e = XWChatConnectionError("connection")
    assert isinstance(e, XWChatProviderError)
    assert isinstance(e, XWChatError)
    assert str(e) == "connection"


def test_errors_can_raise_and_catch() -> None:
    with pytest.raises(XWChatError):
        raise XWChatAgentError("test")
    with pytest.raises(XWChatProviderError):
        raise XWChatConnectionError("conn")
