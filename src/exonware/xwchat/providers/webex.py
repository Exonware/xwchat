#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/webex.py
Cisco Webex Messaging provider using /v1/messages REST API (send only).
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


class WebexChatProvider(AChatProvider):
    """Webex provider using /v1/messages for sending text messages."""

    def __init__(
        self,
        access_token: str,
        *,
        api_base_url: str = "https://webexapis.com/v1",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("Webex access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token
        self._api_base = api_base_url.rstrip("/")
        self._provider_emoji = "💼"
        self._connection_id = self.get_connection_id(access_token)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "webex"

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
            raise XWChatConnectionError("WebexChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        # Simple auth check: GET /people/me
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._api_base}/people/me",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatConnectionError(f"Webex /people/me failed: {resp.status_code} {resp.text}")
            data = resp.json()
            logger.info("%sConnected to Webex as %s", self._log_prefix(), data.get("emails", ["?"])[0])
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Webex: {exc}") from exc

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
        reply_to_message_id: str | None = None,  # can be mapped to parentId for threads
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("WebexChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {"markdown": text}
        # chat_id assumed to be roomId; if it looks like email, use toPersonEmail
        if "@" in chat_id:
            payload["toPersonEmail"] = chat_id
        else:
            payload["roomId"] = chat_id
        if reply_to_message_id:
            payload["parentId"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/messages",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatProviderError(f"Webex /messages failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Webex message: {exc}") from exc

    async def start_listening(self) -> None:
        """Placeholder loop; Webex webhooks receiving requires external configuration and is not implemented."""
        logger.info(
            "%sstart_listening(): Webex receiving via webhooks is not implemented; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

