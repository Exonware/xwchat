#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/discord.py
Discord chat provider implementation using discord.py.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.5
Generation Date: 26-Feb-2026
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError

logger = get_logger(__name__)


class DiscordChatProvider(AChatProvider):
    """Discord chat provider using discord.py.

    Notes (aligned with REF_12_IDEA provider matrix):
    - Auth: Bot token; OAuth2 controls who can add the bot.
    - Delivery: Gateway (WebSocket) for receiving messages.
    - Intents: Message Content intent must be enabled in the Developer Portal.
    - Permissions: View Channels, Send Messages, Read Message History, Attach Files,
      Add Reactions, Create/Send in Threads, etc. are recommended for chat bots.
    - connection_cache_path: When set, the same connection id is reused after crash/restart.
    """

    def __init__(self, token: str, bot_name: str | None = None, connection_cache_path: (str | Path) | None = None) -> None:
        if not token:
            raise ValueError("Discord bot token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._token = token
        self._bot_name = bot_name or "discord"
        self._provider_emoji = "🎮"  # Discord logo (gaming / Clyde)
        self._connection_id = self.get_connection_id(token)
        # Lazily import discord.py in connect() to avoid importing optional deps at module import time.
        self._client: Any | None = None
        self._connected = False
        # Proactive messages to send once gateway is ready (get_channel only populated after on_ready)
        self._pending_proactive: list[tuple[str, str]] = []

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.DISCORD

    @property
    def provider_name(self) -> str:
        return self._bot_name

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        """Discord capabilities per REF_12_IDEA §3.1."""
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.RECEIVE_MESSAGES,
                ChatCapability.SEND_MESSAGES,
                ChatCapability.READ_HISTORY,
                ChatCapability.ATTACHMENTS,
                ChatCapability.THREADS,
                ChatCapability.REACTIONS,
                ChatCapability.COMMANDS,
                ChatCapability.FETCH_MESSAGE_BY_ID,
            }
        )

    async def connect(self) -> None:
        """Create the discord.Client with appropriate intents."""
        if self._client is not None:
            logger.warning("%sclient already created", self._log_prefix())
            return
        try:
            import discord  # type: ignore[import-not-found]
        except ImportError as exc:
            raise XWChatConnectionError("DiscordChatProvider requires discord.py; pip install discord.py") from exc
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        # Ensure we receive message events in guilds (servers)
        if hasattr(intents, "guild_messages"):
            intents.guild_messages = True
        if hasattr(intents, "messages"):
            intents.messages = True
        self._client = discord.Client(intents=intents)

    async def disconnect(self) -> None:
        """Close the Discord client connection."""
        self._listening = False
        self._connected = False
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as exc:
                logger.debug("Error closing Discord client: %s", exc)
            self._client = None

    async def is_connected(self) -> bool:
        return bool(self._client and self._connected)

    def set_pending_proactive_messages(self, messages: list[tuple[str, str]]) -> None:
        """Queue (chat_id, text) pairs to be sent when the gateway is ready (on_ready). Use for startup notifications."""
        self._pending_proactive = list(messages)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a message to a Discord channel (or DM)."""
        if self._client is None:
            raise RuntimeError("Discord: connect() must be called before send_message()")
        channel = self._client.get_channel(int(chat_id))
        if channel is None:
            raise RuntimeError(f"Discord: channel {chat_id} not found")

        # If reply_to_message_id is provided, fetch the message and reply to it;
        # otherwise send a plain message to the channel.
        if reply_to_message_id:
            try:
                msg = await channel.fetch_message(int(reply_to_message_id))  # type: ignore[reportAny]
                return await msg.reply(text, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%scould not send reply, falling back to channel.send: %s", self._log_prefix(), exc)
        return await channel.send(text, **kwargs)  # type: ignore[reportAny]

    async def get_message(self, chat_id: str, message_id: str) -> MessageContext | None:
        """Fetch a message by channel and message id. Returns None if channel not found or message not found."""
        if self._client is None:
            return None
        try:
            channel = self._client.get_channel(int(chat_id))
            if channel is None:
                channel = await self._client.fetch_channel(int(chat_id))
            if channel is None:
                return None
            msg = await channel.fetch_message(int(message_id))  # type: ignore[reportAny]
        except Exception:  # noqa: BLE001
            return None
        is_group = getattr(msg, "guild", None) is not None
        ref = getattr(msg, "reference", None)
        has_reply = bool(ref and getattr(ref, "message_id", None))
        ctx: MessageContext = {
            "chat_id": str(msg.channel.id),
            "user_id": str(msg.author.id),
            "text": msg.content or "",
            "message_id": str(msg.id),
            "username": getattr(msg.author, "name", "") or "",
            "group": is_group,
            "mentioned": False,
            "channel_id": str(msg.channel.id),
            "group_id": str(msg.guild.id) if msg.guild else "",
            "is_reply": has_reply,
        }
        if has_reply:
            ctx["reply_to_message_id"] = str(ref.message_id)
        return ctx

    async def start_listening(self) -> None:
        """Start the Discord gateway and dispatch messages to the handler."""
        if self._client is None:
            raise RuntimeError("Discord: connect() must be called before start_listening()")
        if self._message_handler is None:
            raise RuntimeError("Discord: set_message_handler() must be called before start_listening()")

        client = self._client

        @client.event
        async def on_ready() -> None:  # type: ignore[reportGeneralTypeIssues]
            self._connected = True
            logger.info("%slogged in as %s", self._log_prefix(), client.user)
            for chat_id, text in self._pending_proactive:
                try:
                    ch = client.get_channel(int(chat_id))
                    if ch is None:
                        ch = await client.fetch_channel(int(chat_id))
                    if ch is not None:
                        await ch.send(text)  # type: ignore[reportAny]
                    else:
                        logger.debug("%sproactive to channel %s skipped (not in cache)", self._log_prefix(), chat_id)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%sproactive to %s failed: %s", self._log_prefix(), chat_id, exc)
            self._pending_proactive.clear()

        @client.event
        async def on_message(message: Any) -> None:  # type: ignore[reportGeneralTypeIssues]
            # Log every message event first so we can see if Discord is receiving anything
            channel_name = getattr(message.channel, "name", None) or str(message.channel.id)
            author_name = getattr(message.author, "name", None) or str(message.author)
            has_content = bool(getattr(message, "content", None))
            content_preview = (message.content or "")[:60] if has_content else "(empty)"
            logger.info(
                "%sfrom %r in #%s content=%r len=%s",
                self._log_prefix(),
                author_name,
                channel_name,
                content_preview,
                len(message.content or ""),
            )
            if not has_content:
                logger.warning(
                    "%smessage.content is empty – enable 'Message Content Intent' "
                    "in Developer Portal → your app → Bot → Privileged Gateway Intents",
                    self._log_prefix(),
                )
                return
            if client.user and message.author == client.user:
                return

            self._listening = True
            is_group = message.guild is not None
            mentioned = bool(client.user and client.user in message.mentions)

            ctx: MessageContext = {
                "chat_id": str(message.channel.id),
                "user_id": str(message.author.id),
                "text": message.content,
                "message_id": str(message.id),
                "username": getattr(message.author, "name", "") or "",
                "group": is_group,
                "mentioned": mentioned,
                "channel_id": str(message.channel.id),
                "group_id": str(message.guild.id) if message.guild else "",
            }
            has_reply = bool(message.reference and getattr(message.reference, "message_id", None))
            if has_reply:
                ctx["reply_to_message_id"] = str(message.reference.message_id)
                ctx["is_reply"] = True

            response = self.invoke_message_handler(ctx)
            self.log_message_received(ctx, response is not None)
            if response is None:
                return

            text, reply_to_id, _ = self._normalize_response(response)
            if not text:
                return
            try:
                if reply_to_id:
                    await message.reply(text)
                else:
                    await message.channel.send(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%scould not send response: %s", self._log_prefix(), exc)

        logger.info(
            "%sconnecting to gateway (you should see 'logged in as ...' when ready)...",
            self._log_prefix(),
        )
        self._listening = True
        start_task = asyncio.create_task(client.start(self._token))
        logger.info("%sStarted listening for messages...", self._log_prefix())

        def _discord_done(t: asyncio.Task[Any]) -> None:
            try:
                t.result()
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.error("%sgateway task failed: %s", self._log_prefix(), exc)

        start_task.add_done_callback(_discord_done)
        try:
            while self._listening:
                await asyncio.sleep(1)
        finally:
            await client.close()
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass


# Backwards-compatible alias
Discord = DiscordChatProvider