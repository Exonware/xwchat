#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/google_chat.py
Google Chat provider using incoming webhooks (send-only).

chat_id is expected to be the full incoming webhook URL for the target space.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
import json

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore[assignment]


class GoogleChatProvider(AChatProvider):
    """Google Chat provider using incoming webhook URLs (send-only)."""

    def __init__(
        self,
        default_webhook_url: str | None = None,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        super().__init__(connection_cache_path=connection_cache_path)
        self._default_webhook_url = default_webhook_url or ""
        self._provider_emoji = "💬"
        self._connection_id = self.get_connection_id(self._default_webhook_url or "google_chat")
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "google_chat"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("GoogleChatProvider requires httpx; pip install httpx")
        self._connected = True

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
        reply_to_message_id: str | None = None,  # not used; webhooks are one-way
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("GoogleChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        webhook_url = chat_id or self._default_webhook_url
        if not webhook_url:
            raise XWChatProviderError("GoogleChatProvider requires a webhook URL (chat_id or default_webhook_url)")
        payload: dict[str, Any] = {"text": text}
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    webhook_url,
                    headers={"Content-Type": "application/json; charset=UTF-8"},
                    content=json.dumps(payload),
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Google Chat webhook failed: {resp.status_code} {resp.text}")
            return {"ok": True}
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Google Chat message: {exc}") from exc

    async def start_listening(self) -> None:
        """No receiving for Google Chat webhooks; just keep a passive loop."""
        logger.info(
            "%sstart_listening(): Google Chat incoming webhooks are send-only; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

