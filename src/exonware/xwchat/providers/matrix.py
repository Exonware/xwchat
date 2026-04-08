#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/matrix.py
Matrix chat provider using matrix-nio AsyncClient.

This implementation currently focuses on sending text messages; receiving via sync
loop is left as a future enhancement.
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
    from nio import AsyncClient  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    AsyncClient = None  # type: ignore[assignment]


class MatrixChatProvider(AChatProvider):
    """Matrix provider using matrix-nio (send-only for now)."""

    def __init__(
        self,
        homeserver_url: str,
        access_token: str,
        *,
        user_id: str = "",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not homeserver_url or not access_token:
            raise XWChatProviderError("Matrix homeserver_url and access_token are required")
        if AsyncClient is None:
            raise XWChatProviderError("MatrixChatProvider requires matrix-nio; pip install matrix-nio")
        super().__init__(connection_cache_path=connection_cache_path)
        self._homeserver = homeserver_url
        self._access_token = access_token
        self._user_id = user_id
        self._provider_emoji = "🏗"
        self._connection_id = self.get_connection_id(homeserver_url + "|" + access_token)
        self._client: AsyncClient | None = None
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.MATRIX

    @property
    def provider_name(self) -> str:
        return "matrix"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if AsyncClient is None:
            raise XWChatConnectionError("MatrixChatProvider requires matrix-nio; pip install matrix-nio")
        if self._connected:
            return
        try:
            self._client = AsyncClient(self._homeserver, self._user_id or None)
            self._client.access_token = self._access_token
            logger.info("%sInitialized Matrix client for %s", self._log_prefix(), self._homeserver)
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to initialize Matrix client: {exc}") from exc

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None

    async def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # not used; Matrix threads via relations
        **kwargs: Any,
    ) -> Any:
        if not await self.is_connected():
            await self.connect()
        assert self._client is not None
        content: dict[str, Any] = {"msgtype": "m.text", "body": text}
        content.update(kwargs)
        try:
            resp = await self._client.room_send(
                room_id=chat_id,
                message_type="m.room.message",
                content=content,
            )
            if hasattr(resp, "transport_response") and resp.transport_response is not None:
                code = resp.transport_response.status_code
                if code >= 400:
                    raise XWChatProviderError(f"Matrix room_send failed: {code}")
            return resp
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Matrix message: {exc}") from exc

    async def start_listening(self) -> None:
        """Placeholder loop; receiving via matrix-nio sync is not implemented."""
        logger.info(
            "%sstart_listening(): Matrix receiving via sync is not implemented; "
            "this provider currently supports send_message only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()

