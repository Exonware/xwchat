#!/usr/bin/env python3

from exonware.xwchat.telegram_format import (
    HELP_FORMAT_TELEGRAM_HTML,
    is_telegram_html_help_format,
    merge_telegram_send_kwargs,
    telegram_html_reply,
)


def test_is_telegram_html_help_format() -> None:
    assert is_telegram_html_help_format(HELP_FORMAT_TELEGRAM_HTML) is True
    assert is_telegram_html_help_format("default") is False
    assert is_telegram_html_help_format(None) is False


def test_merge_telegram_send_kwargs_adds_preview_default() -> None:
    out = merge_telegram_send_kwargs({"parse_mode": "HTML"})
    assert out["parse_mode"] == "HTML"
    assert out["disable_web_page_preview"] is True


def test_telegram_html_reply_shape() -> None:
    body, reply_to, kw = telegram_html_reply("<b>Hi</b>")
    assert body == "<b>Hi</b>"
    assert reply_to is None
    assert kw["parse_mode"] == "HTML"
    assert kw["disable_web_page_preview"] is True
