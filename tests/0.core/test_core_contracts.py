#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_contracts.py
Tests that concrete classes implement IChatProvider and IChatAgent protocols.
"""

from __future__ import annotations

import pytest

from exonware.xwchat import (
    IChatAgent,
    IChatProvider,
    XWChatAgent,
)
from exonware.xwchat.providers.dingtalk import DingTalkChatProvider


def test_dingtalk_implements_IChatProvider() -> None:
    p = DingTalkChatProvider("https://example.com/hook")
    assert isinstance(p, IChatProvider)


def test_xwchat_agent_implements_IChatAgent() -> None:
    a = XWChatAgent("A", "Title")
    assert isinstance(a, IChatAgent)


def test_ichat_provider_has_required_attrs() -> None:
    p = DingTalkChatProvider("https://example.com/hook")
    assert hasattr(p, "provider_type")
    assert hasattr(p, "provider_name")
    assert hasattr(p, "capabilities")
    assert hasattr(p, "connection_id")
    assert hasattr(p, "get_connection_id")
    assert hasattr(p, "set_message_handler")
    assert hasattr(p, "should_handle_message")
    assert hasattr(p, "invoke_message_handler")
    assert hasattr(p, "log_message_received")
    assert hasattr(p, "connect")
    assert hasattr(p, "disconnect")
    assert hasattr(p, "is_connected")
    assert hasattr(p, "send_message")
    assert hasattr(p, "get_message")
    assert hasattr(p, "start_listening")
