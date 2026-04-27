#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/viber.py
Viber bot provider using Viber REST Bot API (send_message + webhook).
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
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore[assignment]

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


class ViberChatProvider(AChatProvider):
    """Viber provider using chatapi.viber.com/pa/send_message and webhook callbacks."""

    def __init__(
        self,
        auth_token: str,
        *,
        webhook_port: int = 3005,
        webhook_path: str = "/viber/webhook",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not auth_token:
            raise XWChatProviderError("Viber auth_token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._auth_token = auth_token
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "📱"
        self._connection_id = self.get_connection_id(auth_token)
        self._connected = False
        self._runner: Any = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.CUSTOM

    @property
    def provider_name(self) -> str:
        return "viber"

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
            raise XWChatConnectionError("ViberChatProvider requires httpx; pip install httpx")
        if self._connected:
            return
        # Simple auth check: set webhook URL (caller must configure externally); here we just mark connected.
        self._connected = True
        logger.info("%sViber provider initialized", self._log_prefix())

    async def disconnect(self) -> None:
        self._connected = False
        self._listening = False
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Viber aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return self._connected

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,  # not used; Viber threads via tracking_data
        **kwargs: Any,
    ) -> Any:
        if httpx is None:
            raise XWChatConnectionError("ViberChatProvider requires httpx; pip install httpx")
        await self.connect()
        payload: dict[str, Any] = {
            "receiver": chat_id,
            "type": "text",
            "text": text,
        }
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://chatapi.viber.com/pa/send_message",
                    headers={
                        "X-Viber-Auth-Token": self._auth_token,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            if resp.status_code != 200:
                raise XWChatProviderError(f"Viber send_message failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if data.get("status") != 0:
                raise XWChatProviderError(f"Viber send_message error: {data}")
            return data
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Viber message: {exc}") from exc

    async def start_listening(self) -> None:
        """Start aiohttp webhook server for Viber callbacks."""
        if aiohttp is None:
            raise XWChatConnectionError("ViberChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("ViberChatProvider: set_message_handler() must be called first")
        await self.connect()

        _aio: Any = aiohttp

        async def handle_webhook(request: Any) -> Any:
            try:
                body = await request.json()
            except Exception:
                return _aio.web.Response(status=400, text="Invalid JSON")
            event = body.get("event")
            if event == "webhook":
                # Acknowledge webhook set
                return _aio.web.json_response({"status": 0, "status_message": "ok"})
            if event != "message":
                return _aio.web.json_response({"status": 0})
            msg = body.get("message", {}) or {}
            if msg.get("type") != "text":
                return _aio.web.json_response({"status": 0})
            text = (msg.get("text") or "").strip()
            sender = body.get("sender", {}) or {}
            sender_id = str(sender.get("id", ""))
            ctx: MessageContext = {
                "chat_id": sender_id,
                "user_id": sender_id,
                "text": text,
                "message_id": str(msg.get("token", "")),
                "username": sender.get("name", "") or sender_id,
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
            if text_out:
                try:
                    await self.send_message(sender_id, text_out)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%sCould not send Viber reply: %s", self._log_prefix(), exc)
            return _aio.web.json_response({"status": 0})

        app = aiohttp.web.Application()
        app.router.add_post(self._webhook_path, handle_webhook)
        self._listening = True
        logger.info(
            "%sViber webhook on http://0.0.0.0:%s%s (configure this in Viber bot settings)",
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

