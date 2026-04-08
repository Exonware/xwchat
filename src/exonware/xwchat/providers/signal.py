#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/signal.py
Signal chat provider (send-only).

Signal has no official public bot API. Signal Protocol is E2E encrypted.
This provider documents the limitation; send-only stub for when/if
Signal introduces APIs (e.g. Signal Business API).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)


class SignalChatProvider(AChatProvider):
    """Signal provider (send-only stub). Signal has no official API for bots."""

    def __init__(
        self,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        super().__init__(connection_cache_path=connection_cache_path)
        self._provider_emoji = "🔒"
        self._connection_id = self.get_connection_id("signal")
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "signal"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset({ChatCapability.SEND_MESSAGES})

    async def connect(self) -> None:
        self._connected = True
        logger.info(
            "%sSignal has no official bot API; provider is a send-only stub.",
            self._log_prefix(),
        )

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        raise XWChatProviderError(
            "Signal has no official public bot API; send_message not supported. "
            "Use Signal Business API or third-party bridges if available."
        )

    async def start_listening(self) -> None:
        """Signal has no API for receiving bot messages."""
        logger.info(
            "%sstart_listening(): Signal has no official bot API.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
