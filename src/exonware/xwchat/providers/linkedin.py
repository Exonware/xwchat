#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/linkedin.py
LinkedIn messaging provider using LinkedIn v2 Messages API (partner-only, send-only).

Sending:
- POST https://api.linkedin.com/v2/messages
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


class LinkedInChatProvider(AChatProvider):
    """LinkedIn provider using v2 Messages API (send-only, requires approved partner access)."""

    def __init__(
        self,
        access_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token:
            raise XWChatProviderError("LinkedIn access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token
        self._provider_emoji = "🔗"
        self._connection_id = self.get_connection_id(access_token)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "linkedin"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("LinkedInChatProvider requires httpx; pip install httpx")
        # We assume token validity is managed externally; simple flag here.
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
        reply_to_message_id: str | None = None,  # not used; use thread URN via kwargs when needed
        **kwargs: Any,
    ) -> Any:
        """
        Send a message.

        chat_id is expected to be a person URN (e.g. 'urn:li:person:XXXX').
        """
        if httpx is None:
            raise XWChatConnectionError("LinkedInChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        body: dict[str, Any] = {
            "messageType": "MEMBER_TO_MEMBER",
            "recipients": [chat_id],
            "subject": kwargs.get("subject", ""),
            "body": text,
        }
        if reply_to_message_id:
            body["thread"] = reply_to_message_id
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.linkedin.com/v2/messages",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=body,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"LinkedIn messages API failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending LinkedIn message: {exc}") from exc

    async def start_listening(self) -> None:
        """No public webhook for LinkedIn messaging; keep passive loop."""
        logger.info(
            "%sstart_listening(): LinkedIn receiving is not implemented; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

