#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/reddit.py
Reddit chat provider using PRAW (send-only).

Sends private messages via reddit.redditor(username).message().
Requires OAuth credentials (client_id, client_secret, user_agent).
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
    import praw
except ImportError:  # pragma: no cover - optional dependency
    praw = None  # type: ignore[assignment]


class RedditChatProvider(AChatProvider):
    """Reddit provider using PRAW for private messages (send-only)."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        *,
        username: str | None = None,
        password: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not client_id or not client_secret or not user_agent:
            raise XWChatProviderError("Reddit client_id, client_secret, user_agent required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._user_agent = user_agent.strip()
        self._username = (username or "").strip()
        self._password = (password or "").strip()
        self._provider_emoji = "🔴"
        self._connection_id = self.get_connection_id(self._client_id)
        self._reddit: Any = None
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "reddit"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if praw is None:
            raise XWChatConnectionError("RedditChatProvider requires praw; pip install praw")
        if self._connected:
            return
        kwargs: dict[str, str] = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "user_agent": self._user_agent,
        }
        if self._username and self._password:
            kwargs["username"] = self._username
            kwargs["password"] = self._password
        self._reddit = praw.Reddit(**kwargs)
        self._connected = True
        logger.info("%sConnected to Reddit", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._reddit = None
        self._listening = False

    async def is_connected(self) -> bool:
        return bool(self._connected and self._reddit is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        subject: str = "",
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if praw is None:
            raise XWChatConnectionError("RedditChatProvider requires praw; pip install praw")
        if not await self.is_connected():
            await self.connect()
        assert self._reddit is not None
        subj = subject or kwargs.pop("subject", "Message")
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            redditor = self._reddit.redditor(chat_id)
            result = await loop.run_in_executor(
                None, lambda: redditor.message(subject=subj, message=text)
            )
            return {"id": str(result) if result else None}
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Reddit message: {exc}") from exc

    async def start_listening(self) -> None:
        """Reddit inbox streaming not implemented; send-only."""
        logger.info(
            "%sstart_listening(): Reddit inbox receiving not implemented; send-only.",
            self._log_prefix(),
        )
        self._listening = True
        try:
            while self._listening:
                await asyncio.sleep(5)
        finally:
            await self.disconnect()
