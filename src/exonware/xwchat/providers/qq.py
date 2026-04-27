#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/qq.py
QQ (Tencent) chat provider (send-only).

QQ Open Platform / QQ Bot API: limited to approved bots.
Uses QQ Guild (QQ频道) or QQ Robot API where available.
Fallback: send-only stub when no public API for personal QQ chat.
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


class QQChatProvider(AChatProvider):
    """QQ provider using QQ Open Platform / QQ Guild API (send-only)."""

    def __init__(
        self,
        app_id: str,
        token: str,
        *,
        sandbox: bool = False,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not app_id or not token:
            raise XWChatProviderError("QQ app_id and token are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._app_id = app_id.strip()
        self._token = token.strip()
        self._sandbox = sandbox
        self._api_base = "https://sandbox.api.sgroup.qq.com" if sandbox else "https://api.sgroup.qq.com"
        self._provider_emoji = "🐧"
        self._connection_id = self.get_connection_id(self._app_id)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "qq"

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
            raise XWChatConnectionError("QQChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        self._connected = True
        logger.info("%sConnected to QQ Guild API", self._log_prefix())

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
            raise XWChatConnectionError("QQChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        payload: dict[str, Any] = {
            "content": text,
        }
        if reply_to_message_id:
            payload["msg_id"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/channels/{chat_id}/messages",
                    headers={
                        "Authorization": f"Bot {self._app_id}.{self._token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"QQ API failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending QQ message: {exc}") from exc

    async def start_listening(self) -> None:
        """QQ receiving requires websocket; send-only for now."""
        logger.info(
            "%sstart_listening(): QQ receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
