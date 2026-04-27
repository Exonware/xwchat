#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/rocketchat.py
Rocket.Chat provider implementation using REST API (chat.postMessage).

This implementation currently focuses on sending messages; receiving messages would
require connecting to Rocket.Chat's streaming API and is not included here.
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


class RocketChatProvider(AChatProvider):
    """Rocket.Chat provider using REST chat.postMessage for sending text messages."""

    def __init__(
        self,
        server_url: str,
        user_id: str,
        auth_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not server_url or not user_id or not auth_token:
            raise XWChatProviderError("Rocket.Chat server_url, user_id, and auth_token are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._server_url = server_url.rstrip("/")
        self._user_id = user_id
        self._auth_token = auth_token
        self._provider_emoji = "🚀"
        self._connection_id = self.get_connection_id(self._server_url + "|" + user_id)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "rocketchat"

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
            raise XWChatConnectionError("RocketChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        # Simple auth check: GET /api/v1/me
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._server_url}/api/v1/me",
                    headers={
                        "X-User-Id": self._user_id,
                        "X-Auth-Token": self._auth_token,
                    },
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatConnectionError(f"Rocket.Chat /me failed: {resp.status_code} {resp.text}")
            self._connected = True
            logger.info("%sConnected to Rocket.Chat at %s as %s", self._log_prefix(), self._server_url, self._user_id)
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Rocket.Chat: {exc}") from exc

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
        reply_to_message_id: str | None = None,  # not used; Rocket.Chat supports threads via tmid
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("RocketChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {"text": text}
        # chat_id can be "#channel", "@username", or a roomId; map to "channel"
        payload["channel"] = chat_id
        if reply_to_message_id:
            payload["tmid"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._server_url}/api/v1/chat.postMessage",
                    headers={
                        "X-User-Id": self._user_id,
                        "X-Auth-Token": self._auth_token,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatProviderError(f"Rocket.Chat chat.postMessage failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if not data.get("success"):
                raise XWChatProviderError(f"Rocket.Chat chat.postMessage error: {data}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Rocket.Chat message: {exc}") from exc

    async def start_listening(self) -> None:
        """Placeholder loop; receiving via Rocket.Chat streaming API is not implemented."""
        logger.info(
            "%sstart_listening(): Rocket.Chat streaming API receiving is not implemented; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

