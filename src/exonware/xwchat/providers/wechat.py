#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/wechat.py
WeChat Official Account provider using wechatpy (send-only).

Requires app_id, app_secret; supports custom message to openid.
Note: WeChat Official Account can only send to users who interacted in 48h (or template).
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
    from wechatpy import WeChatClient
    from wechatpy.client.api import WeChatMessage
except ImportError:  # pragma: no cover - optional dependency
    WeChatClient = None  # type: ignore[assignment]
    WeChatMessage = None  # type: ignore[assignment]


class WeChatChatProvider(AChatProvider):
    """WeChat Official Account provider using wechatpy (send-only)."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not app_id or not app_secret:
            raise XWChatProviderError("WeChat app_id and app_secret are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._app_id = app_id.strip()
        self._app_secret = app_secret.strip()
        self._provider_emoji = "💬"
        self._connection_id = self.get_connection_id(self._app_id)
        self._client: Any = None
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "wechat"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if WeChatClient is None:
            raise XWChatConnectionError("WeChatChatProvider requires wechatpy; pip install wechatpy")
        if self._connected:
            return
        self._client = WeChatClient(self._app_id, self._app_secret)
        self._connected = True
        logger.info("%sConnected to WeChat Official Account", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._client = None
        self._listening = False

    async def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if WeChatClient is None:
            raise XWChatConnectionError("WeChatChatProvider requires wechatpy; pip install wechatpy")
        if not await self.is_connected():
            await self.connect()
        assert self._client is not None
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._client.message.send_text(chat_id, text)
            )
            if result.get("errcode", 0) != 0:
                raise XWChatProviderError(f"WeChat API error: {result}")
            return result
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending WeChat message: {exc}") from exc

    async def start_listening(self) -> None:
        """WeChat receiving requires webhook; send-only for now."""
        logger.info(
            "%sstart_listening(): WeChat receiving via webhook not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
