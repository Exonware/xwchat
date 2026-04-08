#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_telegram_utils.py
Unit tests for Telegram provider utilities: _strip_bot_mention, user_exists (mocked).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from exonware.xwchat.providers.telegram import _strip_bot_mention, user_exists


def test_strip_bot_mention_empty_text() -> None:
    assert _strip_bot_mention("", "bot") == ""
    assert _strip_bot_mention("  ", "bot") == ""


def test_strip_bot_mention_empty_bot_username() -> None:
    assert _strip_bot_mention("hello", "") == "hello"


def test_strip_bot_mention_single_mention() -> None:
    assert _strip_bot_mention("@mybot do something", "mybot") == "do something"


def test_strip_bot_mention_case_insensitive() -> None:
    assert _strip_bot_mention("@MyBot cmd", "mybot") == "cmd"
    assert _strip_bot_mention("@MYBOT cmd", "mybot") == "cmd"


def test_strip_bot_mention_multiple() -> None:
    assert _strip_bot_mention("@bot @bot hello", "bot") == "hello"


def test_strip_bot_mention_normalizes_spaces() -> None:
    assert _strip_bot_mention("  @bot   word  ", "bot") == "word"


def test_strip_bot_mention_no_mention_unchanged() -> None:
    text = "hello world"
    assert _strip_bot_mention(text, "otherbot") == text


def test_user_exists_strips_at() -> None:
    with patch("exonware.xwchat.providers.telegram.extract_webpage_text") as m:
        m.return_value = "Send Message"
        assert user_exists("@username") is True
        m.assert_called_once()
        assert "username" in m.call_args[0][0] or "t.me" in m.call_args[0][0]


def test_user_exists_empty_returns_false() -> None:
    assert user_exists("") is False
    assert user_exists("   ") is False


def test_user_exists_false_when_no_send_message() -> None:
    with patch("exonware.xwchat.providers.telegram.extract_webpage_text") as m:
        m.return_value = "Download\nIf you have"
        assert user_exists("user") is False
