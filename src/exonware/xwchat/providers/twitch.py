#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/twitch.py
Twitch chat provider using IRC (send + receive).

Connects to irc-ws.chat.twitch.tv, authenticates with OAuth,
joins channel, sends PRIVMSG. Can receive messages via IRC.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
import json

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)

try:
    import websockets
except ImportError:  # pragma: no cover - optional dependency
    websockets = None  # type: ignore[assignment]


class TwitchChatProvider(AChatProvider):
    """Twitch provider using IRC over WebSocket (send + receive)."""

    def __init__(
        self,
        username: str,
        oauth_token: str,
        *,
        default_channel: str | None = None,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not username or not oauth_token:
            raise XWChatProviderError("Twitch username and oauth_token are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._username = username.strip().lower()
        self._oauth = oauth_token.strip()
        if self._oauth and not self._oauth.startswith("oauth:"):
            self._oauth = f"oauth:{self._oauth}"
        self._default_channel = (default_channel or "").strip().lower()
        self._ws_url = "wss://irc-ws.chat.twitch.tv:443"
        self._provider_emoji = "💜"
        self._connection_id = self.get_connection_id(self._username)
        self._ws: Any = None
        self._connected = False
        self._joined_channels: set[str] = set()

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "twitch"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.SEND_MESSAGES,
                ChatCapability.RECEIVE_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if websockets is None:
            raise XWChatConnectionError("TwitchChatProvider requires websockets; pip install websockets")
        if self._connected and self._ws and self._ws.open:
            return
        self._ws = await websockets.connect(
            self._ws_url,
            ping_interval=60,
            ping_timeout=30,
            close_timeout=5,
        )
        await self._ws.send(f"PASS {self._oauth}\r\n")
        await self._ws.send(f"NICK {self._username}\r\n")
        await self._ws.send("CAP REQ :twitch.tv/commands twitch.tv/tags\r\n")
        self._connected = True
        if self._default_channel:
            await self._join(self._default_channel)
        logger.info("%sConnected to Twitch IRC", self._log_prefix())

    async def _join(self, channel: str) -> None:
        ch = channel if channel.startswith("#") else f"#{channel}"
        if ch not in self._joined_channels and self._ws and self._ws.open:
            await self._ws.send(f"JOIN {ch}\r\n")
            self._joined_channels.add(ch)

    async def disconnect(self) -> None:
        self._listening = False
        self._connected = False
        self._joined_channels.clear()
        if self._ws and self._ws.open:
            await self._ws.close()
        self._ws = None

    async def is_connected(self) -> bool:
        return bool(self._connected and self._ws and self._ws.open)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if websockets is None:
            raise XWChatConnectionError("TwitchChatProvider requires websockets; pip install websockets")
        if not await self.is_connected():
            await self.connect()
        channel = chat_id if chat_id.startswith("#") else f"#{chat_id}"
        await self._join(channel)
        msg = f"PRIVMSG {channel} :{text}\r\n"
        await self._ws.send(msg)
        return {"sent": True}

    async def start_listening(self) -> None:
        """Listen to Twitch IRC messages and dispatch to handler."""
        if websockets is None:
            raise XWChatConnectionError("TwitchChatProvider requires websockets; pip install websockets")
        await self.connect()
        self._listening = True
        try:
            async for raw in self._ws:
                if not self._listening:
                    break
                line = (raw.decode() if isinstance(raw, bytes) else raw).strip()
                if not line:
                    continue
                if line.startswith("PING"):
                    await self._ws.send("PONG :tmi.twitch.tv\r\n")
                    continue
                if " PRIVMSG " in line:
                    parts = line.split(" PRIVMSG ", 1)
                    if len(parts) != 2:
                        continue
                    prefix, rest = parts
                    chan_text = rest.split(" :", 1)
                    channel = chan_text[0].strip()
                    text = chan_text[1] if len(chan_text) > 1 else ""
                    user = prefix.split("!")[0].lstrip(":") if "!" in prefix else ""
                    ctx: MessageContext = {
                        "chat_id": channel,
                        "user_id": user,
                        "text": text,
                        "message_id": "",
                        "username": user,
                        "group": True,
                        "channel": True,
                        "mentioned": f"@{self._username}".lower() in (text or "").lower(),
                    }
                    response = self.invoke_message_handler(ctx)
                    if response:
                        text_out, _, _ = self._normalize_response(response)
                        if text_out:
                            await self.send_message(channel, text_out)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%sTwitch listen error: %s", self._log_prefix(), exc)
        finally:
            await self.disconnect()
