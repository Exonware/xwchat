#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/telegram_channel.py
Telegram Channel provider using Bot API.

Same as TelegramChatProvider but for channels (@channel or -100...).
Uses sendMessage to channel; receiving requires admin + post permissions.
"""

from __future__ import annotations

from pathlib import Path

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

from .telegram import TelegramChatProvider

logger = get_logger(__name__)


class TelegramChannelChatProvider(TelegramChatProvider):
    """Telegram Channel provider; same API as Telegram, chat_id is channel (@channel or -100...)."""

    def __init__(
        self,
        api_token: str,
        *,
        default_channel: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        super().__init__(api_token, connection_cache_path=connection_cache_path)
        self._default_channel = (default_channel or "").strip()
        self._provider_emoji = "📢"

    @property
    def provider_name(self) -> str:
        return "telegram_channel"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return super().capabilities
