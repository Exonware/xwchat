#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_defs.py
Tests for defs: ChatProviderType, ChatCapability, MessageContext, ChatMessageType.
"""

from __future__ import annotations

import pytest

from exonware.xwchat import (
    ChatProviderType,
    ChatCapability,
    MessageContext,
    ChatMessageType,
)


def test_chat_provider_type_values() -> None:
    assert ChatProviderType.TELEGRAM.value == "telegram"
    assert ChatProviderType.WHATSAPP.value == "whatsapp"
    assert ChatProviderType.INSTAGRAM.value == "instagram"
    assert ChatProviderType.DISCORD.value == "discord"
    assert ChatProviderType.SLACK.value == "slack"
    assert ChatProviderType.CUSTOM.value == "custom"


def test_chat_provider_type_members() -> None:
    members = set(ChatProviderType)
    assert len(members) >= 6
    assert ChatProviderType.TELEGRAM in members


def test_chat_capability_members() -> None:
    caps = set(ChatCapability)
    assert ChatCapability.IDENTITY_AUTH in caps
    assert ChatCapability.RECEIVE_MESSAGES in caps
    assert ChatCapability.SEND_MESSAGES in caps
    assert ChatCapability.READ_HISTORY in caps
    assert ChatCapability.ATTACHMENTS in caps
    assert ChatCapability.THREADS in caps
    assert ChatCapability.REACTIONS in caps
    assert ChatCapability.COMMANDS in caps
    assert ChatCapability.FETCH_MESSAGE_BY_ID in caps


def test_message_context_typed_dict() -> None:
    ctx: MessageContext = {}
    ctx["chat_id"] = "c1"
    ctx["user_id"] = "u1"
    ctx["text"] = "hi"
    ctx["message_id"] = "m1"
    ctx["group"] = True
    ctx["mentioned"] = False
    ctx["channel"] = False
    ctx["channel_id"] = "c1"
    ctx["group_id"] = "g1"
    ctx["username"] = "user"
    ctx["reply_to_message_id"] = "m0"
    ctx["is_reply"] = True
    ctx["thread_id"] = "t1"
    assert ctx["chat_id"] == "c1"
    assert ctx["text"] == "hi"


def test_message_context_optional_keys() -> None:
    ctx: MessageContext = {"chat_id": "1", "text": "hello"}
    assert ctx.get("user_id") is None
    assert ctx.get("group") is None


def test_chat_message_type_values() -> None:
    assert ChatMessageType.TEXT.value == "text"
    assert ChatMessageType.IMAGE.value == "image"
    assert ChatMessageType.VIDEO.value == "video"
    assert ChatMessageType.AUDIO.value == "audio"
    assert ChatMessageType.DOCUMENT.value == "document"
    assert ChatMessageType.STICKER.value == "sticker"
    assert ChatMessageType.VOICE.value == "voice"
    assert ChatMessageType.LOCATION.value == "location"
    assert ChatMessageType.CONTACT.value == "contact"


def test_chat_message_type_members() -> None:
    members = set(ChatMessageType)
    assert len(members) >= 9
