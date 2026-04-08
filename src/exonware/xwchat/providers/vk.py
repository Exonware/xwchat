#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/vk.py
VK (VKontakte) chat provider using VK API messages.send (send-only).

Uses VK API 5.x; access_token with messages scope.
chat_id: user_id or peer_id (2000000000 + chat_id for groups).
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


class VKChatProvider(AChatProvider):
    """VK provider using VK API messages.send (send-only)."""

    def __init__(
        self,
        access_token: str,
        *,
        api_version: str = "5.199",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("VK access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token.strip()
        self._api_version = api_version
        self._api_base = "https://api.vk.com/method"
        self._provider_emoji = "🔵"
        self._connection_id = self.get_connection_id(self._access_token[:32])
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "vk"

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
            raise XWChatConnectionError("VKChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._api_base}/users.get",
                params={"access_token": self._access_token, "v": self._api_version},
                timeout=10.0,
            )
        if resp.status_code != 200:
            raise XWChatConnectionError(f"VK auth failed: {resp.status_code}")
        data = resp.json()
        if "error" in data:
            raise XWChatConnectionError(f"VK API error: {data['error']}")
        self._connected = True
        logger.info("%sConnected to VK", self._log_prefix())

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
            raise XWChatConnectionError("VKChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        params: dict[str, Any] = {
            "access_token": self._access_token,
            "v": self._api_version,
            "peer_id": chat_id,
            "message": text,
        }
        if reply_to_message_id:
            params["reply_to"] = reply_to_message_id
        params.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/messages.send",
                    params=params,
                    timeout=10.0,
                )
            data = resp.json()
            if "error" in data:
                raise XWChatProviderError(f"VK messages.send error: {data['error']}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending VK message: {exc}") from exc

    async def start_listening(self) -> None:
        """VK receiving requires Long Poll; send-only for now."""
        logger.info(
            "%sstart_listening(): VK Long Poll receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
