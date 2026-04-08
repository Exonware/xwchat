#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/twilio.py
Twilio chat provider implementation (SMS / WhatsApp) using Twilio REST API + webhook.

Receiving:
- Twilio sends form-encoded webhooks to the configured URL.
Sending:
- Uses twilio.rest.Client to send SMS or WhatsApp messages.
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
    from twilio.rest import Client as TwilioClient
except ImportError:  # pragma: no cover - optional dependency
    TwilioClient = None  # type: ignore[assignment]

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


class TwilioChatProvider(AChatProvider):
    """Twilio provider for SMS / WhatsApp (text only)."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        *,
        webhook_port: int = 3001,
        webhook_path: str = "/twilio/webhook",
        use_whatsapp: bool = False,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not account_sid or not auth_token or not from_number:
            raise XWChatProviderError("Twilio account_sid, auth_token and from_number are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._use_whatsapp = use_whatsapp
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "📞"
        self._connection_id = self.get_connection_id(account_sid + "|" + from_number)
        self._client: TwilioClient | None = None
        self._connected = False
        self._runner: Any = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "twilio"

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
        if TwilioClient is None:
            raise XWChatConnectionError("TwilioChatProvider requires twilio; pip install twilio")
        if self._connected:
            return
        try:
            self._client = TwilioClient(self._account_sid, self._auth_token)
            # Simple auth check: fetch account
            _ = self._client.api.accounts(self._account_sid).fetch()
            logger.info("%sConnected to Twilio account %s", self._log_prefix(), self._account_sid)
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Twilio: {exc}") from exc

    async def disconnect(self) -> None:
        self._listening = False
        self._connected = False
        self._client = None
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Twilio aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # Twilio doesn't have reply threading; ignored
        **kwargs: Any,
    ) -> Any:
        if TwilioClient is None:
            raise XWChatConnectionError("TwilioChatProvider requires twilio; pip install twilio")
        if not await self.is_connected():
            await self.connect()
        assert self._client is not None
        to = chat_id
        if self._use_whatsapp:
            if not to.startswith("whatsapp:"):
                to = "whatsapp:" + to
            from_number = self._from_number
            if not from_number.startswith("whatsapp:"):
                from_number = "whatsapp:" + from_number
        else:
            from_number = self._from_number
        try:
            msg = self._client.messages.create(
                to=to,
                from_=from_number,
                body=text,
                **kwargs,
            )
            return {"sid": msg.sid}
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Twilio message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server to receive Twilio messages."""
        if aiohttp is None:
            raise XWChatConnectionError("TwilioChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("TwilioChatProvider: set_message_handler() must be called first")

        _aio: Any = aiohttp

        async def handle_webhook(request: Any) -> Any:
            # Twilio sends application/x-www-form-urlencoded
            form = await request.post()
            from_number = str(form.get("From", ""))
            to_number = str(form.get("To", ""))
            body = (form.get("Body") or "").strip()
            message_sid = str(form.get("MessageSid", ""))
            if not body:
                return _aio.web.Response(text="", content_type="text/xml")
            is_whatsapp = from_number.startswith("whatsapp:")
            if is_whatsapp:
                from_id = from_number.replace("whatsapp:", "", 1)
            else:
                from_id = from_number
            ctx: MessageContext = {
                "chat_id": from_id,
                "user_id": from_id,
                "text": body,
                "message_id": message_sid,
                "username": from_id,
                "group": False,
                "channel": False,
                "mentioned": True,
                "channel_id": from_id,
                "group_id": "",
            }
            self._listening = True
            response = self.invoke_message_handler(ctx)
            self.log_message_received(ctx, response is not None)
            text_out, _, _ = self._normalize_response(response)
            # Twilio expects TwiML in response to send an immediate reply
            if text_out:
                twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{text_out}</Message></Response>'
                return _aio.web.Response(text=twiml, content_type="text/xml")
            return _aio.web.Response(text="", content_type="text/xml")

        app = aiohttp.web.Application()
        app.router.add_post(self._webhook_path, handle_webhook)
        self._listening = True
        logger.info(
            "%sTwilio webhook on http://0.0.0.0:%s%s (configure this as WhatsApp/SMS webhook URL in Twilio Console)",
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

