#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/instagram.py
Instagram Messaging API provider using Meta Graph API + webhooks.

Sending:
- POST https://graph.facebook.com/v23.0/{IG_BUSINESS_ID}/messages
  (simplified to using a "phone_number_id"-style identifier, configured by the caller).

Receiving:
- Meta webhook for Instagram messaging "messages" events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
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


class InstagramChatProvider(AChatProvider):
    """Instagram Messaging provider using Graph API and webhooks (text only)."""

    def __init__(
        self,
        access_token: str,
        ig_business_id: str,
        *,
        webhook_verify_token: str | None = None,
        webhook_port: int = 3004,
        webhook_path: str = "/instagram/webhook",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not access_token or not ig_business_id:
            raise XWChatProviderError("Instagram access_token and ig_business_id are required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._access_token = access_token
        self._ig_business_id = ig_business_id
        self._webhook_verify_token = webhook_verify_token or os.environ.get(
            "INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "xwchat_verify"
        )
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "📸"
        self._connection_id = self.get_connection_id(access_token + "|" + ig_business_id)
        self._connected = False
        self._runner: Any = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "instagram"

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
            raise XWChatConnectionError("InstagramChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        # Simple auth check: GET /{ig_business_id}?fields=id,name
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://graph.facebook.com/v23.0/{self._ig_business_id}",
                    params={"fields": "id,name", "access_token": self._access_token},
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatConnectionError(f"Instagram get business id failed: {resp.status_code} {resp.text}")
            data = resp.json()
            logger.info("%sConnected to Instagram business %s (%s)", self._log_prefix(), data.get("name"), data.get("id"))
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Instagram: {exc}") from exc

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Instagram aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # not used; conversation context is implicit
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("InstagramChatProvider requires httpx; pip install httpx")
        await self.connect()
        payload: dict[str, Any] = {
            "recipient": {"id": chat_id},
            "message": {"text": text},
        }
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://graph.facebook.com/v23.0/{self._ig_business_id}/messages",
                    params={"access_token": self._access_token},
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatProviderError(f"Instagram send_message failed: {resp.status_code} {resp.text}")
            return resp.json()
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Instagram message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server for Instagram messaging."""
        if aiohttp is None:
            raise XWChatConnectionError("InstagramChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("InstagramChatProvider: set_message_handler() must be called first")
        await self.connect()

        _aio: Any = aiohttp

        async def handle_webhook(request: Any) -> Any:
            if request.method == "GET":
                q = request.rel_url.query
                mode = q.get("hub.mode")
                token = q.get("hub.verify_token")
                challenge = q.get("hub.challenge", "")
                if mode == "subscribe" and token == self._webhook_verify_token:
                    logger.info("%sInstagram webhook verified", self._log_prefix())
                    return _aio.web.Response(text=challenge)
                logger.warning("%sInstagram webhook verification failed", self._log_prefix())
                return _aio.web.Response(status=403, text="Forbidden")

            if request.method != "POST":
                return _aio.web.Response(status=405)

            try:
                body = await request.json()
            except Exception:
                return _aio.web.Response(status=400, text="Invalid JSON")

            if body.get("object") != "instagram":
                return _aio.web.Response(status=200, text="ok")

            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {}) or {}
                    if value.get("field") != "messages":
                        continue
                    for msg in value.get("messages", []):
                        if msg.get("type") != "text":
                            continue
                        text = (msg.get("text") or "").strip()
                        from_id = str(msg.get("from", ""))
                        message_id = str(msg.get("id", ""))
                        if not text:
                            continue
                        ctx: MessageContext = {
                            "chat_id": from_id,
                            "user_id": from_id,
                            "text": text,
                            "message_id": message_id,
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
                        if not text_out:
                            continue
                        try:
                            await self.send_message(from_id, text_out)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("%sCould not send Instagram reply: %s", self._log_prefix(), exc)

            return _aio.web.Response(status=200, text="ok")

        app = aiohttp.web.Application()
        app.router.add_get(self._webhook_path, handle_webhook)
        app.router.add_post(self._webhook_path, handle_webhook)
        self._listening = True
        logger.info(
            "%sInstagram webhook on http://0.0.0.0:%s%s (configure this in your app's Webhooks settings)",
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

