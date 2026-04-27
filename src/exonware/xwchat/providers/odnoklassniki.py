#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/odnoklassniki.py
Odnoklassniki (OK.ru) chat provider (send-only).

OK.ru has limited public messaging API; uses REST where available.
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


class OdnoklassnikiChatProvider(AChatProvider):
    """Odnoklassniki (OK.ru) provider (send-only)."""

    def __init__(
        self,
        access_token: str,
        application_key: str,
        application_secret_key: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token or not application_key or not application_secret_key:
            raise XWChatProviderError("OK access_token, application_key, application_secret_key required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token.strip()
        self._app_key = application_key.strip()
        self._app_secret = application_secret_key.strip()
        self._api_base = "https://api.ok.ru"
        self._provider_emoji = "👥"
        self._connection_id = self.get_connection_id(self._app_key)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "odnoklassniki"

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
            raise XWChatConnectionError("OdnoklassnikiChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to Odnoklassniki", self._log_prefix())

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
            raise XWChatConnectionError("OdnoklassnikiChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        params: dict[str, Any] = {
            "access_token": self._access_token,
            "application_key": self._app_key,
            "chat_id": chat_id,
            "message": text,
        }
        params.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/fb.do",
                    params=params,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"OK API failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if "error_code" in data and data.get("error_code") != 0:
                raise XWChatProviderError(f"OK API error: {data}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending OK message: {exc}") from exc

    async def start_listening(self) -> None:
        """OK receiving not implemented; send-only."""
        logger.info(
            "%sstart_listening(): OK receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
