#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/slack.py
Slack chat provider implementation using Slack Web API + Events API (webhook).

This implementation focuses on text messages:
- Sending via slack_sdk AsyncWebClient (chat.postMessage)
- Receiving via an aiohttp webhook compatible with the Events API

You must:
- Create a Slack app with Bot token + Events API enabled
- Configure the Request URL to point to http://<your-host>:<port><path>
- Subscribe to "message.channels", "message.groups", "message.im", "message.mpim"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Awaitable
import asyncio
import hmac
import hashlib
import json
import time

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError

logger = get_logger(__name__)

try:
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:  # pragma: no cover - optional dependency
    AsyncWebClient = None  # type: ignore[assignment]

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None  # type: ignore[assignment]


class SlackChatProvider(AChatProvider):
    """Slack chat provider using Slack Web API + Events API via aiohttp webhook."""

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        *,
        webhook_port: int = 3000,
        webhook_path: str = "/slack/events",
        connection_cache_path: str | Path | None = None,
    ) -> None:
        if not bot_token:
            raise XWChatProviderError("Slack bot_token is required")
        if not signing_secret:
            raise XWChatProviderError("Slack signing_secret is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._bot_token = bot_token
        self._signing_secret = signing_secret.encode("utf-8")
        self._webhook_port = webhook_port
        self._webhook_path = webhook_path
        self._provider_emoji = "🧵"
        self._connection_id = self.get_connection_id(bot_token)
        self._client: AsyncWebClient | None = None
        self._connected = False
        self._runner: Any = None

    @property
    def provider_type(self) -> ChatProviderType:
        return ChatProviderType.SLACK

    @property
    def provider_name(self) -> str:
        return "slack"

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        return frozenset(
            {
                ChatCapability.IDENTITY_AUTH,
                ChatCapability.RECEIVE_MESSAGES,
                ChatCapability.SEND_MESSAGES,
                ChatCapability.THREADS,
            }
        )

    async def connect(self) -> None:
        """Create AsyncWebClient and validate token."""
        if AsyncWebClient is None:
            raise XWChatConnectionError("SlackChatProvider requires slack_sdk; pip install slack_sdk")
        if self._connected:
            return
        self._client = AsyncWebClient(token=self._bot_token)
        try:
            auth_test = await self._client.auth_test()
            if not auth_test.get("ok"):
                raise XWChatConnectionError(f"Slack auth_test failed: {auth_test}")
            logger.info("%sConnected to Slack as %s", self._log_prefix(), auth_test.get("user"))
            self._connected = True
        except Exception as exc:  # noqa: BLE001
            raise XWChatConnectionError(f"Failed to connect to Slack: {exc}") from exc

    async def disconnect(self) -> None:
        self._listening = False
        self._connected = False
        self._client = None
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Slack aiohttp runner cleanup error: %s", exc)
            self._runner = None

    async def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a message to a Slack channel or DM.

        chat_id: channel id (C...), group (G...), or DM (D...).
        reply_to_message_id: Slack uses thread_ts to reply in a thread; we treat this as ts.
        """
        if AsyncWebClient is None:
            raise XWChatConnectionError("SlackChatProvider requires slack_sdk; pip install slack_sdk")
        if not await self.is_connected():
            await self.connect()
        assert self._client is not None  # for type checkers
        try:
            args: dict[str, Any] = {"channel": chat_id, "text": text}
            if reply_to_message_id:
                args["thread_ts"] = reply_to_message_id
            args.update(kwargs)
            result = await self._client.chat_postMessage(**args)
            if not result.get("ok"):
                raise XWChatProviderError(f"Slack chat_postMessage failed: {result}")
            return result
        except XWChatProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise XWChatProviderError(f"Error sending Slack message: {exc}") from exc

    def _verify_signature(self, timestamp: str, body: bytes, signature: str) -> bool:
        """Verify Slack request signature, per official docs."""
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(time.time() - ts) > 60 * 5:
            return False
        base = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
        expected = "v0=" + hmac.new(self._signing_secret, base, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def start_listening(self) -> None:
        """Start an aiohttp webhook server for Slack Events API."""
        if aiohttp is None:
            raise XWChatConnectionError("SlackChatProvider webhook requires aiohttp; pip install aiohttp")
        if self._message_handler is None:
            raise XWChatProviderError("SlackChatProvider: set_message_handler() must be called first")
        await self.connect()

        _aio: Any = aiohttp

        async def handle_events(request: Any) -> Any:
            # Signature verification
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            signature = request.headers.get("X-Slack-Signature", "")
            body_bytes = await request.read()
            if not self._verify_signature(timestamp, body_bytes, signature):
                logger.warning("%sInvalid Slack signature", self._log_prefix())
                return _aio.web.Response(status=403, text="Invalid signature")

            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                return _aio.web.Response(status=400, text="Invalid JSON")

            # URL verification
            if payload.get("type") == "url_verification":
                return _aio.web.json_response({"challenge": payload.get("challenge", "")})

            if payload.get("type") != "event_callback":
                return _aio.web.Response(status=200, text="ignored")

            event = payload.get("event", {}) or {}
            if event.get("type") != "message":
                return _aio.web.Response(status=200, text="ok")
            if event.get("subtype") in {"message_changed", "message_deleted", "bot_message"}:
                return _aio.web.Response(status=200, text="ok")

            text = (event.get("text") or "").strip()
            if not text:
                return _aio.web.Response(status=200, text="ok")

            channel = str(event.get("channel", ""))
            user = str(event.get("user", ""))
            ts = str(event.get("ts", ""))
            thread_ts = str(event.get("thread_ts", "")) if event.get("thread_ts") else ""
            is_thread = bool(thread_ts and thread_ts != ts)
            is_group = channel.startswith(("C", "G"))

            ctx: MessageContext = {
                "chat_id": channel,
                "user_id": user,
                "text": text,
                "message_id": ts,
                "thread_id": thread_ts or "",
                "username": user,
                "group": is_group,
                "channel": True,
                "mentioned": True,  # Events API already filtered to messages to this bot
                "channel_id": channel,
                "group_id": channel if is_group else "",
            }
            if is_thread:
                ctx["reply_to_message_id"] = thread_ts
                ctx["is_reply"] = True

            self._listening = True
            response = self.invoke_message_handler(ctx)
            self.log_message_received(ctx, response is not None)
            if response is None:
                return _aio.web.Response(status=200, text="ok")
            text_out, reply_to_id, _ = self._normalize_response(response)
            if not text_out:
                return _aio.web.Response(status=200, text="ok")
            try:
                await self.send_message(
                    channel,
                    text_out,
                    reply_to_message_id=reply_to_id or thread_ts or ts,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("%sCould not send Slack reply: %s", self._log_prefix(), exc)
            return _aio.web.Response(status=200, text="ok")

        app = aiohttp.web.Application()
        app.router.add_post(self._webhook_path, handle_events)
        self._listening = True
        logger.info(
            "%sSlack Events webhook on http://0.0.0.0:%s%s (configure this URL in Slack app Events API)",
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

