#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_telegram_format.py
Tests that bot-generated messages (e.g. help) appear correctly in Telegram.

Ensures:
- parse_from_md_format adds parse_mode=Markdown so *bold*, _italic_, `code` render
- prepare_response_for_send applies MD conversion for plain string responses
- Help-like MD content survives the pipeline with correct send kwargs
"""

from __future__ import annotations

import pytest

from exonware.xwchat import TelegramChatProvider

pytestmark = pytest.mark.skipif(
    not hasattr(TelegramChatProvider, "parse_from_md_format"),
    reason="TelegramChatProvider markdown helpers (parse_from_md_format) not in this build",
)


@pytest.fixture
def telegram_provider() -> TelegramChatProvider:
    """Telegram provider with dummy token (no connect/send)."""
    return TelegramChatProvider(api_token="TEST_TOKEN")


def test_parse_from_md_format_adds_parse_mode(telegram_provider: TelegramChatProvider) -> None:
    """parse_from_md_format returns (text, {"parse_mode": "Markdown"}) so Telegram renders *bold* etc."""
    text = "Hello *bold* and _italic_ and `code`"
    formatted, kwargs = telegram_provider.parse_from_md_format(text)
    assert formatted == text
    assert kwargs == {"parse_mode": "Markdown"}


def test_parse_from_md_format_preserves_content(telegram_provider: TelegramChatProvider) -> None:
    """parse_from_md_format does not modify the text, only adds send kwargs."""
    text = "dY- *Bot - Available Commands*\n\n*AGENT Commands:*\n? `/cmd`\n  Summary: Does something"
    formatted, kwargs = telegram_provider.parse_from_md_format(text)
    assert formatted == text
    assert kwargs.get("parse_mode") == "Markdown"


def test_prepare_response_for_send_plain_string(telegram_provider: TelegramChatProvider) -> None:
    """prepare_response_for_send applies parse_from_md_format when handler returns plain string."""
    md_text = "?O *Unknown command:* /xyz\nUse /help for available commands."
    text, reply_to, kwargs = telegram_provider.prepare_response_for_send(md_text)
    assert text == md_text
    assert reply_to is None
    assert kwargs == {"parse_mode": "Markdown"}


def test_prepare_response_for_send_does_not_reparse_when_handler_preformatted(
    telegram_provider: TelegramChatProvider,
) -> None:
    """When handler returns parse_mode, prepare_response_for_send uses as-is (no double conversion)."""
    preformatted = ("Preformatted <b>HTML</b>", None, {"parse_mode": "HTML"})
    text, reply_to, kwargs = telegram_provider.prepare_response_for_send(preformatted)
    assert text == "Preformatted <b>HTML</b>"
    assert kwargs == {"parse_mode": "HTML"}


def test_prepare_response_for_send_help_like_output(telegram_provider: TelegramChatProvider) -> None:
    """Help-like MD output gets parse_mode=Markdown; [roles] are escaped to avoid Telegram parse errors."""
    help_like = (
        "dY- *MyBot - Available Commands*\n\n"
        "*LMAM Commands:*\n"
        "? `/profile` [broadcaster]\n"
        "  Summary: Show user profile\n"
        "? `/help`\n"
        "  Summary: List commands"
    )
    text, reply_to, kwargs = telegram_provider.prepare_response_for_send(help_like)
    assert kwargs.get("parse_mode") == "Markdown"
    assert "MyBot" in text
    assert "`/profile`" in text
    assert r"\[broadcaster\]" in text  # Escaped to avoid 'can'\''t find end of entity'


def test_prepare_response_for_send_error_message(telegram_provider: TelegramChatProvider) -> None:
    """Error messages with *bold* get parse_mode for correct display."""
    error_msg = "?O *Error executing command:*\nsome error details"
    text, reply_to, kwargs = telegram_provider.prepare_response_for_send(error_msg)
    assert text == error_msg
    assert kwargs == {"parse_mode": "Markdown"}


def test_prepare_response_for_send_none(telegram_provider: TelegramChatProvider) -> None:
    """None response returns (None, None, {})."""
    text, reply_to, kwargs = telegram_provider.prepare_response_for_send(None)
    assert text is None
    assert reply_to is None
    assert kwargs == {}


def test_parse_from_md_format_karizma_help_sanitized(telegram_provider: TelegramChatProvider) -> None:
    """Karizma-like help with [optional], [management, owner], year_month, start_date is sanitized for Telegram."""
    help_text = (
        "dY- *Karizma Assistant - Available Commands*\n\n"
        "*LMAM Commands:*\n"
        "? `/rep_broad_mon_u` [management, owner]\n"
        "  Summary: Update monthly broadcasters report\n"
        "  Description: Request, download and update monthly report for active broadcasters\n"
        "  In: year_month (str) [optional]\n"
        "? `/rep_broad_day_u` [management, owner]\n"
        "  In: start_date (str), end_date (str), report_wait (str)\n"
        "\n*Use `/help` to see this message again.*"
    )
    formatted, kwargs = telegram_provider.parse_from_md_format(help_text)
    assert kwargs.get("parse_mode") == "Markdown"
    # Bare [ ] must be escaped to avoid 'can'\''t find end of entity'
    assert r"\[optional\]" in formatted
    assert r"\[management, owner\]" in formatted
    # Underscores in identifiers must be escaped to avoid italic parse errors
    assert r"year\_month" in formatted
    assert r"start\_date" in formatted
    assert r"end\_date" in formatted
    assert r"report\_wait" in formatted
    # Intentional formatting preserved; code blocks unchanged
    assert "*LMAM Commands:*" in formatted
    assert "`/rep_broad_mon_u`" in formatted
