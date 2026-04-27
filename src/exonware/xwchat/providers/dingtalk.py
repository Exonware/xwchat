#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/dingtalk.py
DingTalk custom bot provider using webhook (send-only).

Create a custom bot in DingTalk group → get webhook URL.
POST to webhook with msgtype: text.
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


class DingTalkChatProvider(AChatProvider):
    """DingTalk custom bot provider using webhook URLs (send-only)."""

    def __init__(
        self,
        webhook_url: str,
        *,
        secret: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not webhook_url:
            raise XWChatProviderError("DingTalk webhook_url is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._webhook_url = webhook_url.strip()
        self._secret = (secret or "").strip()
        self._provider_emoji = "🔔"
        self._connection_id = self.get_connection_id(self._webhook_url)
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "dingtalk"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset({ChatCapability.SEND_MESSAGES})

    async def connect(self) -> None:
        if httpx is None:
            raise XWChatConnectionError("DingTalkChatProvider requires httpx; pip install httpx")
        self._connected = True
        logger.info("%sConnected to DingTalk webhook", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False

    async def is_connected(self) -> bool:
        return self._connected

    def _sign_url(self, url: str, secret: str, timestamp: int) -> str:
        """Append timestamp and sign for DingTalk webhook security."""
        import hmac
        import hashlib
        import base64
        import urllib.parse
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}timestamp={timestamp}&sign={sign}"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("DingTalkChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        url = self._webhook_url
        if self._secret:
            import time
            ts = int(time.time() * 1000)
            url = self._sign_url(url, self._secret, ts)
        payload: dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": text},
        }
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"DingTalk webhook failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if data.get("errcode", 0) != 0:
                raise XWChatProviderError(f"DingTalk API error: {data}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending DingTalk message: {exc}") from exc

    async def start_listening(self) -> None:
        """DingTalk custom bots are send-only; no incoming webhook for messages."""
        logger.info(
            "%sstart_listening(): DingTalk custom bot webhooks are send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
