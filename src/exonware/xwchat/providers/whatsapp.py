#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/whatsapp.py
WhatsApp chat provider implementation using Meta Cloud API + webhook.

This class is based on the parrot_bot example connector, adapted to the
shared xwchat abstractions (AChatProvider, MessageContext, ChatCapability).
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
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppChatProvider(AChatProvider):
    """WhatsApp via Meta Cloud API.

    Receives messages via webhook; sends via Graph API.
    This connector is intentionally minimal and focused on text messages.
    """

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        *,
        webhook_verify_token: str = "xwchat_verify",
        webhook_port: int = 8080,
        webhook_path: str = "/webhook",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token or not phone_number_id:
            raise XWChatProviderError("WhatsApp access_token and phone_number_id are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._webhook_verify_token = webhook_verify_token
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path.rstrip("/") or "/webhook"
        self._connection_id = self.get_connection_id(access_token + "|" + phone_number_id)
        self._server: Any = None
        self._runner: Any = None
        self._connected = False

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.WHATSAPP

    @property
    def provider_name(self) -> str:
        return "whatsapp"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        """WhatsApp capabilities (text send/receive only for now)."""
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.RECEIVE_MESSAGES,
                ChatCapability.SEND_MESSAGES,
            }
        )

    async def connect(self) -> None:
        """No persistent outbound connection; webhook server is started in start_listening."""
        if self._connected:
            logger.debug("%salready connected (webhook mode)", self._log_prefix())
            return
        if aiohttp is None:
            raise XWChatConnectionError("WhatsApp requires aiohttp; pip install aiohttp")
        self._connected = True
        logger.info("%sWhatsApp connector initialized (webhook mode)", self._log_prefix())

    async def disconnect(self) -> None:
        """Stop the webhook server and mark as disconnected."""
        self._listening = False
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("%srunner cleanup error: %s", self._log_prefix(), exc)
            self._runner = None
        self._server = None
        self._connected = False
        logger.info("%sWhatsApp connector disconnected", self._log_prefix())

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a text message via WhatsApp Cloud API."""
        if aiohttp is None:
            raise XWChatConnectionError("WhatsApp requires aiohttp; pip install aiohttp")
        if not text:
            raise XWChatProviderError("Cannot send empty WhatsApp message")
        url = f"{GRAPH_API_BASE}/{self._phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id.lstrip("+").replace(" ", ""),
            "type": "text",
            "text": {"body": text[:4096]},
        }
        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        raise XWChatProviderError(
                            f"WhatsApp send_message failed with status {resp.status}: {body}"
                        )
                    return await resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending WhatsApp message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server and dispatch messages to handler."""
        if aiohttp is None:
            raise XWChatConnectionError("WhatsApp webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("Set message handler first (set_message_handler)")

        _aio: Any = aiohttp  # local alias for closure

        async def handle_webhook(request: Any) -> Any:
            # Verification (GET)
            if request.method == "GET":
                q = request.rel_url.query
                if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == self._webhook_verify_token:
                    challenge = q.get("hub.challenge", "")
                    logger.info("%sWebhook verified via GET", self._log_prefix())
                    return _aio.web.Response(text=challenge)
                logger.warning("%sWebhook verification failed", self._log_prefix())
                return _aio.web.Response(status=403, text="Forbidden")

            # Notifications (POST)
            if request.method != "POST":
                return _aio.web.Response(status=405)

            try:
                body = await request.json()
            except Exception:
                logger.warning("%sInvalid JSON webhook payload", self._log_prefix())
                return _aio.web.Response(status=400, text="Invalid JSON")

            if body.get("object") != "whatsapp_business_account":
                return _aio.web.Response(status=200, text="ok")

            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") != "messages":
                        continue
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    phone_number_id = str(metadata.get("phone_number_id", ""))
                    if phone_number_id != self._phone_number_id:
                        continue
                    for msg in value.get("messages", []):
                        self._listening = True
                        if msg.get("type") != "text":
                            continue
                        text_obj = msg.get("text", {}) or {}
                        text = (text_obj.get("body") or "").strip()
                        from_id = str(msg.get("from", ""))
                        message_id = str(msg.get("id", ""))
                        contacts = value.get("contacts", [])
                        profile_name = ""
                        for c in contacts:
                            if str(c.get("wa_id")) == from_id:
                                profile_name = (c.get("profile") or {}).get("name", "") or ""
                                break
                        is_group = False  # Cloud API 1:1; group payload differs
                        ctx: MessageContext = {
                            "chat_id": from_id,
                            "user_id": from_id,
                            "text": text,
                            "message_id": message_id,
                            "username": profile_name,
                            "group": is_group,
                            "mentioned": False,
                            "channel": False,
                            "channel_id": from_id,
                            "group_id": "",
                        }
                        if msg.get("context", {}).get("id"):
                            ctx["reply_to_message_id"] = str(msg["context"]["id"])
                            ctx["is_reply"] = True
                        response = self.invoke_message_handler(ctx)
                        self.log_message_received(ctx, response is not None)
                        if response is None:
                            continue
                        text_out, reply_to_id, _ = self._normalize_response(response)
                        if not text_out:
                            continue
                        try:
                            await self.send_message(from_id, text_out, reply_to_message_id=reply_to_id)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("%sCould not send WhatsApp reply: %s", self._log_prefix(), exc)

            return _aio.web.Response(status=200, text="ok")

        app = aiohttp.web.Application()
        app.router.add_get(self._webhook_path, handle_webhook)
        app.router.add_post(self._webhook_path, handle_webhook)
        self._listening = True
        await self.connect()
        logger.info(
            "%sWebhook server on http://0.0.0.0:%s%s (configure this URL in Meta app; use ngrok for local)",
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


# Backwards-compatible alias
WhatsApp = WhatsAppChatProvider

