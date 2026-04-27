#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/messenger.py
Facebook Messenger chat provider using Meta Graph Send API + webhooks.

Sending:
- POST https://graph.facebook.com/v23.0/me/messages?access_token=PAGE_ACCESS_TOKEN

Receiving:
- Meta Webhook that handles GET verification and POST "messages" events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
import json
import os

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore[assignment]

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


class MessengerChatProvider(AChatProvider):
    """Facebook Messenger provider using Graph Send API and webhooks."""

    def __init__(
        self,
        page_access_token: str,
        *,
        webhook_verify_token: str | None = None,
        webhook_port: int = 3003,
        webhook_path: str = "/messenger/webhook",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not page_access_token:
            raise XWChatProviderError("Messenger page_access_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._page_access_token = page_access_token
        self._webhook_verify_token = webhook_verify_token or os.environ.get(
            "MESSENGER_WEBHOOK_VERIFY_TOKEN", "xwchat_verify"
        )
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "📩"
        self._connection_id = self.get_connection_id(page_access_token)
        self._connected = False
        self._runner: Any = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "messenger"

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
        if httpx is None:
            raise XWChatConnectionError("MessengerChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        # Simple auth check: GET /me?fields=id,name
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://graph.facebook.com/v23.0/me",
                    params={"fields": "id,name", "access_token": self._page_access_token},
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatConnectionError(f"Messenger /me failed: {resp.status_code} {resp.text}")
            data = resp.json()
            logger.info("%sConnected to Messenger page %s (%s)", self._log_prefix(), data.get("name"), data.get("id"))
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Messenger: {exc}") from exc

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Messenger aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # not used; Messenger threads by conversation
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("MessengerChatProvider requires httpx; pip install httpx")
        await self.connect()
        payload: dict[str, Any] = {
            "recipient": {"id": chat_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://graph.facebook.com/v23.0/me/messages",
                    params={"access_token": self._page_access_token},
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatProviderError(f"Messenger send_message failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Messenger message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server for Messenger."""
        if aiohttp is None:
            raise XWChatConnectionError("MessengerChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("MessengerChatProvider: set_message_handler() must be called first")
        await self.connect()

        _aio: Any = aiohttp

        async def handle_webhook(request: Any) -> Any:
            if request.method == "GET":
                q = request.rel_url.query
                mode = q.get("hub.mode")
                token = q.get("hub.verify_token")
                challenge = q.get("hub.challenge", "")
                if mode == "subscribe" and token == self._webhook_verify_token:
                    logger.info("%sMessenger webhook verified", self._log_prefix())
                    return _aio.web.Response(text=challenge)
                logger.warning("%sMessenger webhook verification failed", self._log_prefix())
                return _aio.web.Response(status=403, text="Forbidden")

            if request.method != "POST":
                return _aio.web.Response(status=405)

            try:
                body = await request.json()
            except Exception:
                return _aio.web.Response(status=400, text="Invalid JSON")

            if body.get("object") != "page":
                return _aio.web.Response(status=200, text="ok")

            for entry in body.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender = messaging.get("sender", {}) or {}
                    recipient = messaging.get("recipient", {}) or {}
                    message = messaging.get("message", {}) or {}
                    if not message.get("text"):
                        continue
                    sender_id = str(sender.get("id", ""))
                    text = (message.get("text") or "").strip()
                    mid = str(message.get("mid", ""))
                    ctx: MessageContext = {
                        "chat_id": sender_id,
                        "user_id": sender_id,
                        "text": text,
                        "message_id": mid,
                        "username": sender_id,
                        "group": False,
                        "channel": False,
                        "mentioned": True,
                        "channel_id": sender_id,
                        "group_id": "",
                    }
                    self._listening = True
                    response = self.invoke_message_handler(ctx)
                    self.log_message_received(ctx, response is not None)
                    text_out, _, _ = self._normalize_response(response)
                    if not text_out:
                        continue
                    try:
                        await self.send_message(sender_id, text_out)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("%sCould not send Messenger reply: %s", self._log_prefix(), exc)

            return _aio.web.Response(status=200, text="ok")

        app = aiohttp.web.Application()
        app.router.add_get(self._webhook_path, handle_webhook)
        app.router.add_post(self._webhook_path, handle_webhook)
        self._listening = True
        logger.info(
            "%sMessenger webhook on http://0.0.0.0:%s%s (configure this in App → Webhooks → messages)",
            self._log_prefix(),
            self._webhook_port,
            self._webhook_path,
        )
        self._runner = aiohttp.web.AppRunner(app)
        await self._runner.setup()
        site = aiohttp.web.TCPSite(self._runner, "0.0.0.0", self._webhook_port)
        await site.start()
        try:
            while self._listening:
                await asyncio.sleep(1)
        finally:
            await self.disconnect()

