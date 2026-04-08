#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/tiktok.py
TikTok chat provider (send-only).

TikTok has Messaging API for business/creators.
Uses TikTok for Developers API when available.
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


class TikTokChatProvider(AChatProvider):
    """TikTok provider using Messaging API (send-only)."""

    def __init__(
        self,
        access_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("TikTok access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token.strip()
        self._api_base = "https://open.tiktokapis.com"
        self._provider_emoji = "🎵"
        self._connection_id = self.get_connection_id(self._access_token[:16])
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "tiktok"

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
            raise XWChatConnectionError("TikTokChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to TikTok (messaging API limited)", self._log_prefix())

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
        if httpx is None:
            raise XWChatConnectionError("TikTokChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {
            "recipient": {"user_id": chat_id},
            "message": {"text": text},
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/v2/message/send/",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"TikTok API failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending TikTok message: {exc}") from exc

    async def start_listening(self) -> None:
        """TikTok receiving requires webhook; send-only for now."""
        logger.info(
            "%sstart_listening(): TikTok receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
