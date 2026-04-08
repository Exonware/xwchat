#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/threema.py
Threema Gateway API provider (send-only).

Uses threema.gateway SDK or REST for simple (server-side encrypted) messages.
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


class ThreemaChatProvider(AChatProvider):
    """Threema provider using Gateway API (send-only)."""

    def __init__(
        self,
        gateway_id: str,
        api_secret: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not gateway_id or not api_secret:
            raise XWChatProviderError("Threema gateway_id and api_secret are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._gateway_id = gateway_id.strip()
        self._api_secret = api_secret.strip()
        self._api_base = "https://msgapi.threema.ch"
        self._provider_emoji = "🔵"
        self._connection_id = self.get_connection_id(self._gateway_id)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "threema"

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
            raise XWChatConnectionError("ThreemaChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to Threema Gateway", self._log_prefix())

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
            raise XWChatConnectionError("ThreemaChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        params: dict[str, str] = {
            "from": self._gateway_id,
            "secret": self._api_secret,
            "to": chat_id,
            "text": text,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._api_base}/send_simple",
                    params=params,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Threema API failed: {resp.status_code} {resp.text}")
            return {"message_id": resp.text.strip()}
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Threema message: {exc}") from exc

    async def start_listening(self) -> None:
        """Threema receiving requires callback URL; send-only for now."""
        logger.info(
            "%sstart_listening(): Threema receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
