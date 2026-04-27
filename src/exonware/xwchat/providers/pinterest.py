#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/pinterest.py
Pinterest messaging provider (send-only).

Pinterest has limited messaging API for business accounts.
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


class PinterestChatProvider(AChatProvider):
    """Pinterest messaging provider (send-only)."""

    def __init__(
        self,
        access_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("Pinterest access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token.strip()
        self._api_base = "https://api.pinterest.com"
        self._provider_emoji = "📌"
        self._connection_id = self.get_connection_id(self._access_token[:16])
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "pinterest"

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
            raise XWChatConnectionError("PinterestChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info(
            "%sPinterest messaging API is limited; provider is send-only.",
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
        if httpx is None:
            raise XWChatConnectionError("PinterestChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {
            "recipient_id": chat_id,
            "message": {"text": text},
        }
        if reply_to_message_id:
            payload["reply_to"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/v5/conversations/send",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Pinterest API failed: {resp.status_code} {resp.text}")
            return resp.json() if resp.content else {"ok": True}
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Pinterest message: {exc}") from exc

    async def start_listening(self) -> None:
        """Pinterest receiving not implemented; send-only."""
        logger.info(
            "%sstart_listening(): Pinterest receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
