#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_async_lifecycle.py
Async lifecycle tests: connect, disconnect, is_connected, get_message (default) for multiple providers.
"""

from __future__ import annotations

import pytest

from exonware.xwchat.providers.dingtalk import DingTalkChatProvider
from exonware.xwchat.providers.teams import TeamsChatProvider
from exonware.xwchat.providers.signal import SignalChatProvider


@pytest.mark.asyncio
async def test_dingtalk_connect_disconnect_is_connected() -> None:
    p = DingTalkChatProvider("https://example.com/hook")
    assert await p.is_connected() is False
    await p.connect()
    assert await p.is_connected() is True
    await p.disconnect()
    assert await p.is_connected() is False


@pytest.mark.asyncio
async def test_teams_connect_is_connected() -> None:
    p = TeamsChatProvider()
    await p.connect()
    assert await p.is_connected() is True
    await p.disconnect()
    assert await p.is_connected() is False


@pytest.mark.asyncio
async def test_signal_connect_disconnect() -> None:
    p = SignalChatProvider()
    await p.connect()
    assert await p.is_connected() is True
    await p.disconnect()
    assert await p.is_connected() is False


@pytest.mark.asyncio
async def test_get_message_default_none() -> None:
    """Default get_message returns None for providers that do not override."""
    p = DingTalkChatProvider("https://example.com/hook")
    out = await p.get_message("chat1", "msg1")
    assert out is None
