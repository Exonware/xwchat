#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/line.py
LINE Messaging API chat provider implementation using line-bot-sdk and aiohttp webhook.

Receiving:
- LINE sends JSON webhooks with signature header X-Line-Signature.
Sending:
- Uses line-bot-sdk v3 MessagingApi.
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
    from linebot.v3 import WebhookHandler
    from linebot.v3.messaging import (
        Configuration,
        ApiClient,
        MessagingApi,
        ReplyMessageRequest,
        TextMessage,
    )
    from linebot.v3.webhooks import MessageEvent, TextMessageContent
    from linebot.v3.exceptions import InvalidSignatureError
except ImportError:  # pragma: no cover - optional dependency
    WebhookHandler = None  # type: ignore[assignment]

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


class LineChatProvider(AChatProvider):
    """LINE Messaging API provider (text only)."""

    def __init__(
        self,
        channel_access_token: str,
        channel_secret: str,
        *,
        webhook_port: int = 3002,
        webhook_path: str = "/line/callback",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not channel_access_token or not channel_secret:
            raise XWChatProviderError("LINE channel_access_token and channel_secret are required")
        if WebhookHandler is None:
            raise XWChatProviderError("LineChatProvider requires line-bot-sdk; pip install line-bot-sdk")
        super().__init__(connection_cache_path=connection_cache_path)
        self._channel_access_token = channel_access_token
        self._channel_secret = channel_secret
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "💬"
        self._connection_id = self.get_connection_id(channel_access_token + "|" + channel_secret)
        self._configuration = Configuration(access_token=self._channel_access_token)
        self._handler = WebhookHandler(self._channel_secret)
        self._connected = False
        self._runner: Any = None

        @self._handler.add(MessageEvent, message=TextMessageContent)
        def _on_message(event: MessageEvent) -> None:  # noqa: D401
            """Internal handler that adapts LINE event → MessageContext and dispatches to AChatProvider handler."""
            try:
                user_id = event.source.user_id or ""
                chat_id = event.source.group_id or event.source.room_id or user_id
                text = (event.message.text or "").strip()
                message_id = event.message.id or ""
                is_group = bool(event.source.group_id or event.source.room_id)
                ctx: MessageContext = {
                    "chat_id": str(chat_id),
                    "user_id": str(user_id),
                    "text": text,
                    "message_id": str(message_id),
                    "username": str(user_id),
                    "group": is_group,
                    "channel": False,
                    "mentioned": True,
                    "channel_id": str(chat_id),
                    "group_id": str(chat_id) if is_group else "",
                }
                self._listening = True
                response = self.invoke_message_handler(ctx)
                self.log_message_received(ctx, response is not None)
                text_out, _, _ = self._normalize_response(response)
                if not text_out:
                    return
                # Use reply_token (LINE requires reply API for immediate replies)
                with ApiClient(self._configuration) as api_client:
                    api = MessagingApi(api_client)
                    api.reply_message_with_http_info(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=text_out)],
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("%sError handling LINE message: %s", self._log_prefix(), exc)

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "line"

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
        # No explicit network connect step; MessagingApi is created per request
        self._connected = True
        logger.info("%sLINE provider initialized", self._log_prefix())

    async def disconnect(self) -> None:
        self._listening = False
        self._connected = False
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("LINE aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # LINE uses reply_token, not id; this is ignored
        **kwargs: Any,
    ) -> Any:
        # For proactive messages, chat_id is userId / roomId / groupId; use pushMessage.
        try:
            with ApiClient(self._configuration) as api_client:
                api = MessagingApi(api_client)
                # There is a dedicated push API, but current v3 SDK exposes push_message_with_http_info via MessagingApi
                api.push_message_with_http_info(
                    to=chat_id,
                    messages=[TextMessage(text=text, **kwargs)],
                )
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending LINE message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server for LINE Messaging API."""
        if aiohttp is None:
            raise XWChatConnectionError("LineChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("LineChatProvider: set_message_handler() must be called first")
        await self.connect()

        _aio: Any = aiohttp

        async def handle_callback(request: Any) -> Any:
            signature = request.headers.get("X-Line-Signature", "")
            body = await request.text()
            try:
                self._handler.handle(body, signature)
            except InvalidSignatureError:
                logger.warning("%sInvalid LINE signature", self._log_prefix())
                return _aio.web.Response(status=400, text="Invalid signature")
            return _aio.web.Response(text="OK")

        app = aiohttp.web.Application()
        app.router.add_post(self._webhook_path, handle_callback)
        self._listening = True
        logger.info(
            "%sLINE webhook on http://0.0.0.0:%s%s (configure this as your Messaging API webhook URL)",
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

