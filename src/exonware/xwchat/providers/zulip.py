#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/zulip.py
Zulip chat provider implementation using python-zulip-api.

Receiving:
- Uses Zulip Client.call_on_each_message in a background thread to get message events.
Sending:
- Uses Client.send_message to send messages to streams or private messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import asyncio
import threading

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)

try:
    import zulip
except ImportError:  # pragma: no cover - optional dependency
    zulip = None  # type: ignore[assignment]


class ZulipChatProvider(AChatProvider):
    """Zulip provider using python-zulip-api."""

    def __init__(
        self,
        site: str,
        email: str,
        api_key: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not site or not email or not api_key:
            raise XWChatProviderError("Zulip site, email, and api_key are required")
        if zulip is None:
            raise XWChatProviderError("ZulipChatProvider requires python-zulip-api; pip install zulip")
        super().__init__(connection_cache_path=connection_cache_path)
        self._site = site
        self._email = email
        self._api_key = api_key
        self._provider_emoji = "📨"
        self._connection_id = self.get_connection_id(site + "|" + email)
        self._client: zulip.Client | None = None  # type: ignore[assignment]
        self._connected = False
        self._listener_thread: threading.Thread | None = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "zulip"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.RECEIVE_MESSAGES,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        if self._connected:
            return
        try:
            self._client = zulip.Client(
                site=self._site,
                email=self._email,
                api_key=self._api_key,
            )
            # Simple auth check: get own profile
            resp = self._client.get_profile()
            if resp.get("result") != "success":
                raise XWChatConnectionError(f"Zulip get_profile failed: {resp}")
            logger.info("%sConnected to Zulip realm %s as %s", self._log_prefix(), self._site, self._email)
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Zulip: {exc}") from exc

    async def disconnect(self) -> None:
        self._listening = False
        self._connected = False
        self._client = None
        if self._listener_thread is not None:
            # call_on_each_message loop will end when _listening is False; we don't force-join
            self._listener_thread = None

    async def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # use in_reply_to if provided
        **kwargs: Any,
    ) -> Any:
        if not await self.is_connected():
            await self.connect()
        assert self._client is not None
        # chat_id can be "stream:<name>" or "pm:<user_id>" or a raw stream/user id; we support simple patterns.
        msg: dict[str, Any] = {"content": text}
        if chat_id.startswith("stream:"):
            msg["type"] = "stream"
            msg["to"] = chat_id.split(":", 1)[1]
        elif chat_id.startswith("pm:"):
            # pm:email1,email2
            emails = chat_id.split(":", 1)[1]
            msg["type"] = "private"
            msg["to"] = [e.strip() for e in emails.split(",") if e.strip()]
        else:
            # assume stream name
            msg["type"] = "stream"
            msg["to"] = chat_id
        if reply_to_message_id:
            msg["topic"] = kwargs.get("topic") or "reply"
            msg["in_reply_to"] = int(reply_to_message_id) if reply_to_message_id.isdigit() else reply_to_message_id
        msg.update(kwargs)
        try:
            result = self._client.send_message(msg)
            if result.get("result") != "success":
                raise XWChatProviderError(f"Zulip send_message failed: {result}")
            return result
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Zulip message: {exc}") from exc

    def _start_listener_thread(self, loop: asyncio.AbstractEventLoop) -> None:
        assert self._client is not None

        def handle_message(event: dict[str, Any]) -> None:
            if event.get("type") != "message":
                return
            msg = event.get("message", {}) or {}
            text = (msg.get("content") or "").strip()
            if not text:
                return
            msg_id = str(msg.get("id", ""))
            sender_id = str(msg.get("sender_id", ""))
            sender_full_name = msg.get("sender_full_name", "") or ""
            stream_id = msg.get("stream_id")
            chat_id = ""
            is_group = False
            if msg.get("type") == "stream":
                chat_id = str(stream_id or "")
                is_group = True
            else:
                # private
                chat_id = sender_id
            ctx: MessageContext = {
                "chat_id": chat_id,
                "user_id": sender_id,
                "text": text,
                "message_id": msg_id,
                "username": sender_full_name or sender_id,
                "group": is_group,
                "channel": False,
                "mentioned": True,
                "channel_id": chat_id,
                "group_id": chat_id if is_group else "",
            }
            response = self.invoke_message_handler(ctx)
            self.log_message_received(ctx, response is not None)
            if response is None:
                return
            text_out, _, _ = self._normalize_response(response)

            if not text_out:
                return

            async def _send_reply() -> None:
                try:
                    await self.send_message(chat_id, text_out)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%sError sending Zulip reply: %s", self._log_prefix(), exc)

            asyncio.run_coroutine_threadsafe(_send_reply(), loop)

        def run() -> None:
            try:
                self._client.call_on_each_message(handle_message)  # type: ignore[union-attr]
            except Exception as exc:  # noqa: BLE001
                logger.warning("%sZulip listener stopped: %s", self._log_prefix(), exc)

        self._listener_thread = threading.Thread(target=run, name="ZulipChatProviderListener", daemon=True)
        self._listener_thread.start()

    async def start_listening(self) -> None:
        """Start Zulip long-poll listener in a background thread."""
        if self._message_handler is None:
            raise XWChatProviderError("ZulipChatProvider: set_message_handler() must be called first")
        await self.connect()
        assert self._client is not None
        self._listening = True
        loop = asyncio.get_running_loop()
        self._start_listener_thread(loop)
        logger.info("%sStarted Zulip long-poll listener", self._log_prefix())
        try:
            while self._listening:
                await asyncio.sleep(1)
        finally:
            await self.disconnect()

