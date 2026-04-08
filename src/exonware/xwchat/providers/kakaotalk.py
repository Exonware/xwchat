#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/kakaotalk.py
Kakao Talk Message API provider (send-only).

Uses Kakao Developers REST API; requires app key and recipient UUID.
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


class KakaoTalkChatProvider(AChatProvider):
    """Kakao Talk provider using Kakao Message API (send-only)."""

    def __init__(
        self,
        rest_api_key: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not rest_api_key:
            raise XWChatProviderError("KakaoTalk rest_api_key is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._rest_api_key = rest_api_key.strip()
        self._api_base = "https://kapi.kakao.com"
        self._provider_emoji = "💛"
        self._connection_id = self.get_connection_id(self._rest_api_key[:16])
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "kakaotalk"

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
            raise XWChatConnectionError("KakaoTalkChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to Kakao Talk", self._log_prefix())

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
            raise XWChatConnectionError("KakaoTalkChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        import json
        payload: dict[str, Any] = {
            "object_type": "text",
            "text": text,
            "link": {"web_url": "", "mobile_web_url": ""},
        }
        if kwargs:
            payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/v2/api/talk/memo/default/send",
                    headers={
                        "Authorization": f"KakaoAK {self._rest_api_key}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"template_object": json.dumps(payload)},
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Kakao API failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Kakao message: {exc}") from exc

    async def start_listening(self) -> None:
        """Kakao receiving not implemented; send-only."""
        logger.info(
            "%sstart_listening(): Kakao receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
