#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/imessage.py
iMessage / Apple Business Chat provider (send-only).

Apple Business Chat uses Business Chat API / JMS (Journey Management API).
Requires Apple Business Chat credentials; limited to approved businesses.
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


class IMessageChatProvider(AChatProvider):
    """iMessage / Apple Business Chat provider (send-only)."""

    def __init__(
        self,
        api_key: str,
        org_id: str,
        *,
        api_base: str = "https://api.businesschat.apple.com",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not api_key or not org_id:
            raise XWChatProviderError("Apple Business Chat api_key and org_id are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._api_key = api_key.strip()
        self._org_id = org_id.strip()
        self._api_base = api_base.rstrip("/")
        self._provider_emoji = "💬"
        self._connection_id = self.get_connection_id(self._org_id)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "imessage"

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
            raise XWChatConnectionError("IMessageChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to Apple Business Chat", self._log_prefix())

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
            raise XWChatConnectionError("IMessageChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {
            "destinationId": chat_id,
            "message": {"body": text, "type": "text"},
        }
        if reply_to_message_id:
            payload["replyToMessageId"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/v1/message",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Apple Business Chat failed: {resp.status_code} {resp.text}")
            return resp.json() if resp.content else {"ok": True}
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending iMessage: {exc}") from exc

    async def start_listening(self) -> None:
        """Apple Business Chat receiving requires webhook; send-only for now."""
        logger.info(
            "%sstart_listening(): Apple Business Chat receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()


AppleBusinessChatProvider = IMessageChatProvider
