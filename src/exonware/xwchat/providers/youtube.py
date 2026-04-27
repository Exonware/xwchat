#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/youtube.py
YouTube Live Chat provider using YouTube Data API v3 (send-only).

Uses liveChatMessages.insert to post to a live stream's chat.
Requires OAuth with youtube scope; chat_id is liveChatId.
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

# Note: google deps are imported lazily inside methods to avoid importing optional
# third-party packages (and their warnings) during xwchat import.
Credentials = None  # type: ignore[assignment]
build = None  # type: ignore[assignment]
HttpError = Exception  # type: ignore[assignment]


class YouTubeChatProvider(AChatProvider):
    """YouTube Live Chat provider using Data API v3 (send-only)."""

    def __init__(
        self,
        credentials_json_path: str | None = None,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        super().__init__(connection_cache_path=connection_cache_path)
        self._creds_path = (credentials_json_path or "").strip()
        self._access_token = (access_token or "").strip()
        self._refresh_token = (refresh_token or "").strip()
        self._client_id = (client_id or "").strip()
        self._client_secret = (client_secret or "").strip()
        self._provider_emoji = "▶️"
        self._connection_id = self.get_connection_id(self._creds_path or self._access_token[:16] or "youtube")
        self._youtube: Any = None
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "youtube"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    def _get_credentials(self) -> Any:
        try:
            from google.oauth2.credentials import Credentials as _Credentials  # type: ignore[import-not-found]
            from googleapiclient.discovery import build as _build  # type: ignore[import-not-found]
        except ImportError as exc:
            raise XWChatConnectionError("YouTubeChatProvider requires google-api-python-client, google-auth") from exc
        if self._creds_path:
            from google.oauth2 import service_account  # type: ignore[import-not-found]
            return service_account.Credentials.from_service_account_file(
                self._creds_path,
                scopes=["https://www.googleapis.com/auth/youtube"],
            )
        if self._access_token:
            return _Credentials(
                token=self._access_token,
                refresh_token=self._refresh_token or None,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_id or None,
                client_secret=self._client_secret or None,
            )
        raise XWChatProviderError("YouTube requires credentials_json_path or access_token")

    async def connect(self) -> None:
        try:
            from googleapiclient.discovery import build as _build  # type: ignore[import-not-found]
        except ImportError as exc:
            raise XWChatConnectionError("YouTubeChatProvider requires google-api-python-client") from exc
        if self._connected:
            return
        creds = self._get_credentials()
        self._youtube = _build("youtube", "v3", credentials=creds)
        self._connected = True
        logger.info("%sConnected to YouTube Live Chat API", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._youtube = None
        self._listening = False

    async def is_connected(self) -> bool:
        return bool(self._connected and self._youtube is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if build is None:
            raise XWChatConnectionError("YouTubeChatProvider requires google-api-python-client")
        if not await self.is_connected():
            await self.connect()
        assert self._youtube is not None
        body = {
            "snippet": {
                "liveChatId": chat_id,
                "type": "text",
                "textMessageDetails": {"messageText": text},
            }
        }
        import asyncio
        try:
            def _send():
                return (
                    self._youtube.liveChatMessages()
                    .insert(part="snippet", body=body)
                    .execute()
                )
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _send)
            return result
        except HttpError as exc:
            raise XWChatProviderError(f"YouTube API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending YouTube message: {exc}") from exc

    async def start_listening(self) -> None:
        """YouTube Live Chat polling not implemented; send-only."""
        logger.info(
            "%sstart_listening(): YouTube Live Chat receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
