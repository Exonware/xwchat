#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_base.py
Tests for AChatProvider and AChatAgent base behavior.

Uses concrete providers (e.g. DingTalkChatProvider) to exercise base class
methods: set_agent_id, get_connection_id, connection_id, _log_prefix,
should_handle_message, invoke_message_handler, _normalize_response,
log_message_received, set_message_handler, get_message (default).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from exonware.xwchat import AChatProvider, MessageContext
from exonware.xwchat.providers.dingtalk import DingTalkChatProvider


@pytest.fixture
def provider_no_cache() -> DingTalkChatProvider:
    """Provider with no connection cache (get_connection_id returns generated id)."""
    return DingTalkChatProvider("https://example.com/webhook")


@pytest.fixture
def provider_with_cache(tmp_path: Path) -> DingTalkChatProvider:
    """Provider with connection_cache_path set."""
    cache_file = tmp_path / "conn_cache.json"
    return DingTalkChatProvider("https://example.com/webhook", connection_cache_path=cache_file)


def test_set_agent_id(provider_no_cache: DingTalkChatProvider) -> None:
    """set_agent_id updates _agent_id and _log_prefix reflects it."""
    p = provider_no_cache
    assert getattr(p, "_agent_id", None) is None
    p.set_agent_id("my_bot")
    assert p._agent_id == "my_bot"
    assert "my_bot" in p._log_prefix()


def test_connection_id_without_cache(provider_no_cache: DingTalkChatProvider) -> None:
    """connection_id is set from get_connection_id when no cache path."""
    p = provider_no_cache
    assert p.connection_id != ""
    assert "dingtalk" in p.connection_id


def test_get_connection_id_stable_without_cache(provider_no_cache: DingTalkChatProvider) -> None:
    """Same key yields same connection id when no cache (deterministic digest)."""
    p = provider_no_cache
    key = "same_key"
    id1 = p.get_connection_id(key)
    id2 = p.get_connection_id(key)
    assert id1 == id2
    assert "dingtalk" in id1


def test_get_connection_id_with_cache_reuses(provider_with_cache: DingTalkChatProvider) -> None:
    """With cache path, same key reuses stored connection id."""
    p = provider_with_cache
    key = "token123"
    id1 = p.get_connection_id(key)
    id2 = p.get_connection_id(key)
    assert id1 == id2
    assert p._connection_cache_path is not None
    assert p._connection_cache_path.exists()


def test_connection_id_property(provider_no_cache: DingTalkChatProvider) -> None:
    """connection_id property returns _connection_id set by subclass."""
    p = provider_no_cache
    assert p.connection_id == getattr(p, "_connection_id", "")


def test_log_prefix_without_agent_id(provider_no_cache: DingTalkChatProvider) -> None:
    """_log_prefix contains provider name when agent_id not set."""
    p = provider_no_cache
    prefix = p._log_prefix()
    assert "dingtalk" in prefix


def test_log_prefix_with_agent_id(provider_no_cache: DingTalkChatProvider) -> None:
    """_log_prefix contains agent_id when set."""
    p = provider_no_cache
    p.set_agent_id("parrot")
    prefix = p._log_prefix()
    assert "parrot" in prefix
    assert "dingtalk" in prefix


def test_should_handle_message_channel_true(provider_no_cache: DingTalkChatProvider) -> None:
    """In channel context, should_handle_message returns True."""
    p = provider_no_cache
    ctx: MessageContext = {"channel": True}
    assert p.should_handle_message(ctx) is True


def test_should_handle_message_group_mentioned_true(provider_no_cache: DingTalkChatProvider) -> None:
    """In group when mentioned, should_handle_message returns True."""
    p = provider_no_cache
    ctx: MessageContext = {"group": True, "mentioned": True}
    assert p.should_handle_message(ctx) is True


def test_should_handle_message_group_not_mentioned_false(provider_no_cache: DingTalkChatProvider) -> None:
    """In group when not mentioned, should_handle_message returns False."""
    p = provider_no_cache
    ctx: MessageContext = {"group": True, "mentioned": False}
    assert p.should_handle_message(ctx) is False


def test_should_handle_message_dm_true(provider_no_cache: DingTalkChatProvider) -> None:
    """DM (no group/channel) returns True."""
    p = provider_no_cache
    ctx: MessageContext = {}
    assert p.should_handle_message(ctx) is True


def test_invoke_message_handler_no_handler_returns_none(provider_no_cache: DingTalkChatProvider) -> None:
    """invoke_message_handler returns None when no handler set."""
    p = provider_no_cache
    ctx: MessageContext = {"chat_id": "1", "text": "hi"}
    assert p.invoke_message_handler(ctx) is None


def test_invoke_message_handler_skipped_when_should_not_handle(provider_no_cache: DingTalkChatProvider) -> None:
    """invoke_message_handler returns None when should_handle_message is False."""
    p = provider_no_cache
    p.set_message_handler(lambda ctx: "reply")
    ctx: MessageContext = {"group": True, "mentioned": False}
    assert p.invoke_message_handler(ctx) is None


def test_invoke_message_handler_returns_str(provider_no_cache: DingTalkChatProvider) -> None:
    """invoke_message_handler returns handler result when handler returns str."""
    p = provider_no_cache
    p.set_message_handler(lambda ctx: "hello")
    ctx: MessageContext = {"chat_id": "1", "text": "hi"}
    assert p.invoke_message_handler(ctx) == "hello"


def test_invoke_message_handler_returns_tuple(provider_no_cache: DingTalkChatProvider) -> None:
    """invoke_message_handler returns (text, reply_to_id) when handler returns tuple."""
    p = provider_no_cache
    p.set_message_handler(lambda ctx: ("reply", "msg_123"))
    ctx: MessageContext = {"chat_id": "1", "text": "hi"}
    assert p.invoke_message_handler(ctx) == ("reply", "msg_123")


def test_normalize_response_none() -> None:
    """_normalize_response(None) returns (None, None, {})."""
    out = DingTalkChatProvider._normalize_response(None)
    assert out == (None, None, {})


def test_normalize_response_str() -> None:
    """_normalize_response(str) returns (str, None, {})."""
    out = DingTalkChatProvider._normalize_response("hello")
    assert out == ("hello", None, {})


def test_normalize_response_tuple() -> None:
    """_normalize_response((a, b)) returns (a, b, {})."""
    out = DingTalkChatProvider._normalize_response(("text", "reply_id"))
    assert out == ("text", "reply_id", {})


def test_normalize_response_tuple_none_reply() -> None:
    """_normalize_response((text, None)) returns (text, None, {})."""
    out = DingTalkChatProvider._normalize_response(("text", None))
    assert out == ("text", None, {})


def test_log_message_received_no_raise(provider_no_cache: DingTalkChatProvider) -> None:
    """log_message_received does not raise."""
    p = provider_no_cache
    ctx: MessageContext = {"chat_id": "c1", "user_id": "u1", "text": "hi"}
    p.log_message_received(ctx, True)
    p.log_message_received(ctx, False)


def test_set_message_handler(provider_no_cache: DingTalkChatProvider) -> None:
    """set_message_handler stores callable."""
    p = provider_no_cache
    handler = lambda ctx: "ok"
    p.set_message_handler(handler)
    assert p._message_handler is handler


@pytest.mark.asyncio
async def test_get_message_default_returns_none(provider_no_cache: DingTalkChatProvider) -> None:
    """Default get_message returns None (base implementation)."""
    p = provider_no_cache
    out = await p.get_message("chat_id", "msg_id")
    assert out is None
