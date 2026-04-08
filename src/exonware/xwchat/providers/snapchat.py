#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/snapchat.py
Snapchat chat provider (send-only).

Snapchat has limited APIs (Creative Kit, Marketing API).
Messaging API is restricted; send-only stub for when/if available.
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

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore[assignment]


class SnapchatChatProvider(AChatProvider):
    """Snapchat provider (send-only). Snapchat messaging API is restricted."""

    def __init__(
        self,
        access_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("Snapchat access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token.strip()
        self._api_base = "https://adsapi.snapchat.com"
        self._provider_emoji = "👻"
        self._connection_id = self.get_connection_id(self._access_token[:16])
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "snapchat"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("SnapchatChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info(
            "%sSnapchat messaging API is restricted; provider is send-only stub.",
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
            "Snapchat does not expose a public messaging API for bots. "
            "Use Snapchat Marketing API or Creative Kit for limited integrations."
        )

    async def start_listening(self) -> None:
        """Snapchat has no public messaging receive API."""
        logger.info(
            "%sstart_listening(): Snapchat messaging API not available.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
