#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/x_twitter.py
X (Twitter) DM provider using Twitter API v2 direct messages endpoints (send-only).

Sending:
- POST https://api.x.com/2/dm_conversations/with/:participant_id/messages
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


class XTwitterChatProvider(AChatProvider):
    """X (Twitter) provider using v2 DM send endpoint (send-only)."""

    def __init__(
        self,
        bearer_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not bearer_token:
            raise XWChatProviderError("X/Twitter bearer_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._bearer_token = bearer_token
        self._provider_emoji = "🐦"
        self._connection_id = self.get_connection_id(bearer_token)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "x_twitter"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("XTwitterChatProvider requires httpx; pip install httpx")
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
        reply_to_message_id: str | None = None,  # not used; conversation id can be passed via kwargs
        **kwargs: Any,
    ) -> Any:
        """
        Send a DM to a user.

        chat_id is expected to be the recipient's user ID (participant_id).
        """
        if httpx is None:
            raise XWChatConnectionError("XTwitterChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        url = f"https://api.x.com/2/dm_conversations/with/{chat_id}/messages"
        body: dict[str, Any] = {"text": text}
        body.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._bearer_token}",
                        "Content-Type": "application/json",
                    },
                    json={"message": body},
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"X DM send failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending X DM: {exc}") from exc

    async def start_listening(self) -> None:
        """Receiving DMs requires Account Activity / webhooks; not implemented."""
        logger.info(
            "%sstart_listening(): X/Twitter DM receiving is not implemented; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

