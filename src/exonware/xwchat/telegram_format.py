#!/usr/bin/env python3
"""
Telegram Bot API send helpers (parse_mode, defaults).

Transport-agnostic beyond Telegram's HTML mode contract — no bot-framework imports.
"""

from __future__ import annotations

from typing import Any

HELP_FORMAT_TELEGRAM_HTML = "telegram_html"


def is_telegram_html_help_format(help_format: str | None) -> bool:
    """True when command context requests Telegram HTML replies."""
    return (help_format or "").strip() == HELP_FORMAT_TELEGRAM_HTML


def merge_telegram_send_kwargs(send_kwargs: dict[str, Any] | None) -> dict[str, Any]:
    """Merge caller send kwargs with safe defaults for long bot replies (Telegram Bot API)."""
    out = dict(send_kwargs or ())
    if out.get("parse_mode") and "disable_web_page_preview" not in out:
        out["disable_web_page_preview"] = True
    return out


def telegram_html_reply(
    body: str,
    *,
    disable_web_page_preview: bool = True,
    **extra_send_kwargs: Any,
) -> tuple[str, None, dict[str, Any]]:
    """
    Tuple form consumed by :class:`exonware.xwchat.providers.telegram.TelegramChatProvider`
    when formatting outbound messages.
    """
    kwargs: dict[str, Any] = {
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_web_page_preview,
    }
    kwargs.update(extra_send_kwargs)
    return (body, None, kwargs)
