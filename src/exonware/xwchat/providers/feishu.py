#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/feishu.py
Feishu/Lark chat provider using Open Platform REST API (send-only).

Requires app_id, app_secret; obtains tenant_access_token for API calls.
Send to open_id, user_id, or chat_id (group).
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


class FeishuChatProvider(AChatProvider):
    """Feishu/Lark provider using Open Platform REST API (send-only)."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        api_base: str = "https://open.feishu.cn",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not app_id or not app_secret:
            raise XWChatProviderError("Feishu app_id and app_secret are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._app_id = app_id.strip()
        self._app_secret = app_secret.strip()
        self._api_base = api_base.rstrip("/")
        self._provider_emoji = "🪶"
        self._connection_id = self.get_connection_id(self._app_id)
        self._connected = False
        self._access_token: str | None = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "feishu"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def _get_tenant_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        if httpx is None:
            raise XWChatConnectionError("FeishuChatProvider requires httpx; pip install httpx")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_base}/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self._app_id, "app_secret": self._app_secret},
                timeout=10.0,
            )
        if resp.status_code != 200:
            raise XWChatConnectionError(f"Feishu token failed: {resp.status_code} {resp.text}")
        data = resp.json()
        if data.get("code", -1) != 0:
            raise XWChatConnectionError(f"Feishu token error: {data}")
        self._access_token = data.get("tenant_access_token", "")
        return self._access_token

    async def connect(self) -> None:
        if self._connected:
            return
        await self._get_tenant_access_token()
        self._connected = True
        logger.info("%sConnected to Feishu/Lark", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._access_token = None
        self._listening = False

    async def is_connected(self) -> bool:
        return bool(self._connected and self._access_token)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        receive_id_type: str = "chat_id",
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("FeishuChatProvider requires httpx; pip install httpx")
        if not await self.is_connected():
            await self.connect()
        token = await self._get_tenant_access_token()
        receive_id_type = kwargs.pop("receive_id_type", receive_id_type)
        if chat_id.startswith("ou_"):
            receive_id_type = "open_id"
        elif chat_id.startswith("oc_"):
            receive_id_type = "chat_id"
        else:
            receive_id_type = "user_id"
        payload: dict[str, Any] = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": {"text": text},
        }
        if reply_to_message_id:
            payload["root_id"] = reply_to_message_id
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._api_base}/open-apis/im/v1/messages",
                    params={"receive_id_type": receive_id_type},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code >= 400:
                raise XWChatProviderError(f"Feishu send failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if data.get("code", -1) != 0:
                raise XWChatProviderError(f"Feishu API error: {data}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Feishu message: {exc}") from exc

    async def start_listening(self) -> None:
        """Feishu receiving requires Event subscription; send-only for now."""
        logger.info(
            "%sstart_listening(): Feishu receiving via events not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()


LarkChatProvider = FeishuChatProvider
