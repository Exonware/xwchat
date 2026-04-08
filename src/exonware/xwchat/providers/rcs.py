#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/rcs.py
RCS (Rich Communication Services) Business Messaging provider (send-only).

Uses Google RCS Business Messaging API or carrier RBM APIs.
Requires agent ID and service account / API credentials.
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


class RCSChatProvider(AChatProvider):
    """RCS Business Messaging provider (send-only)."""

    def __init__(
        self,
        agent_id: str,
        credentials_json_path: str | None = None,
        *,
        api_key: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not agent_id:
            raise XWChatProviderError("RCS agent_id is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._agent_id = agent_id.strip()
        self._creds_path = (credentials_json_path or "").strip()
        self._api_key = (api_key or "").strip()
        self._api_base = "https://rcsbusinessmessaging.googleapis.com"
        self._provider_emoji = "📱"
        self._connection_id = self.get_connection_id(self._agent_id)
        self._connected = False
        self._access_token: str | None = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "rcs"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self._creds_path:
            raise XWChatProviderError("RCS requires credentials_json_path for OAuth")
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            self._creds_path,
            scopes=["https://www.googleapis.com/auth/rcsbusinessmessaging"],
        )
        creds.refresh(None)
        self._access_token = creds.token
        return self._access_token

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("RCSChatProvider requires httpx; pip install httpx")
        if self._creds_path:
            await self._get_token()
        self._connected = True
        logger.info("%sConnected to RCS Business Messaging", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._access_token = None
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
            raise XWChatConnectionError("RCSChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        url = f"{self._api_base}/v1/phones/{chat_id}/agentMessages"
        payload: dict[str, Any] = {
            "messageId": kwargs.pop("message_id", ""),
            "text": text,
        }
        payload.update(kwargs)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self._api_key:
            url += f"?key={self._api_key}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if resp.status_code >= 400:
                raise XWChatProviderError(f"RCS API failed: {resp.status_code} {resp.text}")
            return resp.json() if resp.content else {"ok": True}
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending RCS message: {exc}") from exc

    async def start_listening(self) -> None:
        """RCS receiving requires webhook; send-only for now."""
        logger.info(
            "%sstart_listening(): RCS receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
