#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/skype.py
Skype / Microsoft Bot Framework provider (send-only).

Uses Bot Framework Connector REST API.
Requires Microsoft App ID and password; chat_id is serviceUrl + conversationId.
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


class SkypeChatProvider(AChatProvider):
    """Skype provider using Bot Framework Connector API (send-only)."""

    def __init__(
        self,
        app_id: str,
        app_password: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not app_id or not app_password:
            raise XWChatProviderError("Skype app_id and app_password are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._app_id = app_id.strip()
        self._app_password = app_password.strip()
        self._connector_base = "https://smba.trafficmanager.net/apis"
        self._provider_emoji = "💬"
        self._connection_id = self.get_connection_id(self._app_id)
        self._connected = False
        self._token: str | None = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "skype"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        if httpx is None:
            raise XWChatConnectionError("SkypeChatProvider requires httpx; pip install httpx")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._app_id,
                    "client_secret": self._app_password,
                    "scope": "https://api.botframework.com/.default",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        if resp.status_code != 200:
            raise XWChatConnectionError(f"Skype token failed: {resp.status_code} {resp.text}")
        data = resp.json()
        self._token = data.get("access_token", "")
        return self._token

    async def connect(self) -> None:
        if self._connected:
            return
        await self._get_token()
        self._connected = True
        logger.info("%sConnected to Skype Bot Framework", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._token = None
        self._listening = False

    async def is_connected(self) -> bool:
        return bool(self._connected and self._token)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        service_url: str | None = None,
        conversation_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("SkypeChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        if service_url and conversation_id:
            conv_id = conversation_id
            svc = service_url
        else:
            conv_id = chat_id
            svc = service_url or "https://smba.trafficmanager.net/apis"
        token = await self._get_token()
        payload: dict[str, Any] = {
            "type": "message",
            "text": text,
        }
        if reply_to_message_id:
            payload["replyToId"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{svc}/v3/conversations/{conv_id}/activities",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Skype send failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Skype message: {exc}") from exc

    async def start_listening(self) -> None:
        """Skype receiving requires Bot Framework webhook; send-only for now."""
        logger.info(
            "%sstart_listening(): Skype receiving via webhook not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
