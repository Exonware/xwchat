#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_dingtalk.py
Unit tests for DingTalkChatProvider: _sign_url, connect, disconnect, is_connected.
"""

from __future__ import annotations

import time

import pytest

from exonware.xwchat.providers.dingtalk import DingTalkChatProvider


def test_dingtalk_sign_url_append_query() -> None:
    """_sign_url appends timestamp and sign to URL without existing query."""
    p = DingTalkChatProvider("https://oapi.dingtalk.com/robot/send")
    url = p._sign_url("https://example.com/hook", "secret", 1234567890000)
    assert "timestamp=1234567890000" in url
    assert "sign=" in url
    assert "?" in url
    assert "https://example.com/hook?" in url


def test_dingtalk_sign_url_with_existing_query() -> None:
    """_sign_url uses & when URL already has ?."""
    p = DingTalkChatProvider("https://example.com/hook")
    base = "https://example.com/hook?foo=bar"
    url = p._sign_url(base, "s", 1)
    assert "&timestamp=" in url
    assert "&sign=" in url


@pytest.mark.asyncio
async def test_dingtalk_connect_disconnect_is_connected() -> None:
    """connect sets _connected True; disconnect sets False; is_connected reflects."""
    p = DingTalkChatProvider("https://example.com/hook")
    assert await p.is_connected() is False
    await p.connect()
    assert await p.is_connected() is True
    await p.disconnect()
    assert await p.is_connected() is False
