#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_telegram_pause_queue.py
Unit tests: pause inbound queue, operator resume drain, command/args logging helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from exonware.xwchat import TelegramChatProvider


def _dm_message(
    *,
    user_id: int,
    text: str,
    message_id: int = 1,
    chat_id: int = 4242,
) -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.chat = MagicMock()
    msg.chat.type = "private"
    msg.chat.id = chat_id
    msg.chat.title = None
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = "tester"
    msg.from_user.first_name = "T"
    msg.message_id = message_id
    msg.date = datetime.now(timezone.utc)
    msg.reply_to_message = None
    msg.entities = None
    msg.reply_text = AsyncMock(return_value=None)
    return msg


@pytest.fixture
def operator_ids() -> frozenset[int]:
    return frozenset({900001})


@pytest.fixture
def paused_provider(tmp_path: Path, operator_ids: frozenset[int]) -> TelegramChatProvider:
    return TelegramChatProvider(
        api_token="TEST_TOKEN_PAUSE",
        data_path=str(tmp_path),
        auto_save_users=False,
        enable_message_logging=False,
        enable_json_audit_log=False,
        telegram_operator_user_ids=operator_ids,
        max_paused_inbound_queue=50,
    )


def test_command_and_args_for_log_slash_command(paused_provider: TelegramChatProvider) -> None:
    assert paused_provider._command_and_args_for_log("/roles scout") == ("roles", "scout")
    assert paused_provider._command_and_args_for_log("/help@MyBot x") == ("help", "x")


def test_command_and_args_for_log_plain_text(paused_provider: TelegramChatProvider) -> None:
    cmd, args = paused_provider._command_and_args_for_log("  hello world  ")
    assert cmd == "(message)"
    assert args.startswith("hello world")


def test_command_and_args_for_log_empty(paused_provider: TelegramChatProvider) -> None:
    assert paused_provider._command_and_args_for_log("") == ("", "")
    assert paused_provider._command_and_args_for_log("   ") == ("", "")


@pytest.mark.asyncio
async def test_operator_pause_resume_drains_fifo(
    paused_provider: TelegramChatProvider,
    operator_ids: frozenset[int],
) -> None:
    handled: list[str] = []

    def handler(ctx: dict) -> None:
        handled.append(str(ctx.get("text", "")))
        return None

    paused_provider.set_message_handler(handler)
    op_id = next(iter(operator_ids))

    pause_msg = _dm_message(user_id=op_id, text="/pause", message_id=10)
    assert await paused_provider._maybe_handle_privileged_telegram_commands(
        pause_msg,
        user_id_str=str(op_id),
        command_text="/pause",
        bot_username="",
        bot_id=None,
    )
    assert paused_provider._processing_paused is True
    pause_msg.reply_text.assert_awaited()

    u1 = _dm_message(user_id=7, text="/echo one", message_id=11)
    u2 = _dm_message(user_id=8, text="/echo two", message_id=12)
    await paused_provider._process_incoming_text_update(u1, "", None)
    await paused_provider._process_incoming_text_update(u2, "", None)
    assert len(paused_provider._paused_inbound_queue) == 2
    assert handled == []
    u1.reply_text.assert_awaited()
    u2.reply_text.assert_awaited()

    resume_msg = _dm_message(user_id=op_id, text="/resume", message_id=13)
    assert await paused_provider._maybe_handle_privileged_telegram_commands(
        resume_msg,
        user_id_str=str(op_id),
        command_text="/resume",
        bot_username="",
        bot_id=None,
    )
    assert paused_provider._processing_paused is False
    assert len(paused_provider._paused_inbound_queue) == 0
    assert handled == ["/echo one", "/echo two"]


@pytest.mark.asyncio
async def test_paused_queue_respects_max_length(tmp_path: Path) -> None:
    p = TelegramChatProvider(
        api_token="TEST_TOKEN_PAUSE",
        data_path=str(tmp_path),
        auto_save_users=False,
        enable_message_logging=False,
        enable_json_audit_log=False,
        telegram_operator_user_ids=frozenset(),
        max_paused_inbound_queue=2,
    )
    p._processing_paused = True
    m1 = _dm_message(user_id=1, text="/a", message_id=1)
    m2 = _dm_message(user_id=1, text="/b", message_id=2)
    m3 = _dm_message(user_id=1, text="/c", message_id=3)
    await p._process_incoming_text_update(m1, "", None)
    await p._process_incoming_text_update(m2, "", None)
    await p._process_incoming_text_update(m3, "", None)
    assert len(p._paused_inbound_queue) == 2
    m3.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_operator_pending_shows_queue_snapshot(
    paused_provider: TelegramChatProvider,
    operator_ids: frozenset[int],
) -> None:
    op_id = next(iter(operator_ids))
    paused_provider._processing_paused = True
    paused_provider._paused_inbound_queue.append(
        {
            "msg": None,
            "text": "/foo bar",
            "user_id_str": "77",
            "chat_id_str": "42",
        }
    )
    msg = _dm_message(user_id=op_id, text="/pending", message_id=50)
    assert await paused_provider._maybe_handle_privileged_telegram_commands(
        msg,
        user_id_str=str(op_id),
        command_text="/pending",
        bot_username="",
        bot_id=None,
    )
    msg.reply_text.assert_awaited()
    body = str(msg.reply_text.await_args[0][0])
    assert "1 item" in body or "1 item(s)" in body
    assert "user 77" in body
    assert "/foo bar" in body


@pytest.mark.asyncio
async def test_emit_transport_status_forwards_command_args_to_sink(tmp_path: Path) -> None:
    events: list[tuple[str, str, dict]] = []

    async def sink(status: str, message: str, **kw: object) -> None:
        events.append((status, message, dict(kw)))

    p = TelegramChatProvider(
        api_token="TEST_TOKEN",
        data_path=str(tmp_path),
        auto_save_users=False,
        enable_message_logging=False,
        enable_json_audit_log=False,
        transport_status_sink=sink,
    )
    await p._emit_transport_status("test_status", "hello", command="pause", args="n=3", extra_key=1)
    assert len(events) == 1
    st, msg, kw = events[0]
    assert st == "test_status"
    assert msg == "hello"
    assert kw.get("command") == "pause"
    assert kw.get("args") == "n=3"
    assert kw.get("extra_key") == 1
