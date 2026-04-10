#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/base.py
Abstract base classes for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.3
Generation Date: 07-Jan-2025
"""

import hashlib
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

# When run as a script (python base.py), relative imports fail; use absolute imports and add src to path.
if __name__ == "__main__":
    _src = Path(__file__).resolve().parent.parent.parent  # .../xwchat/src
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from exonware.xwsystem import get_logger
    from exonware.xwsystem.io.serialization import JsonSerializer
    from exonware.xwchat.contracts import IChatAgent, IChatProvider
    from exonware.xwchat.defs import ChatCapability, ChatProviderType, MessageContext
else:
    from exonware.xwsystem import get_logger
    from exonware.xwsystem.io.serialization import JsonSerializer
    from .contracts import IChatAgent, IChatProvider
    from .defs import ChatCapability, ChatProviderType, MessageContext

HandlerResponse = str | tuple[str, str | None] | tuple[str, str | None, dict[str, Any]] | None

_logger = get_logger(__name__)


class AChatProvider(IChatProvider, ABC):
    """
    Abstract base for chat providers (REF_12_IDEA §2, §3; parrot_bot surface).

    MessageContext: Providers populate chat_id, user_id, text, message_id when available,
    and group (True if channel/server, not DM) and mentioned (True if bot was @mentioned)
    so should_handle_message applies: in groups the handler is only invoked when the bot is mentioned.

    Reply semantics: MessageContext can carry reply_to_message_id; send_message() accepts
    reply_to_message_id for outgoing replies.

    Connection cache: When connection_cache_path is set, get_connection_id() reads and writes
    stable connection IDs to that JSON file. After a crash or restart, the same provider+key
    reuses the same connection id from the cache so there is no conflicting connection
    (single logical connection per provider+token). Format:
    { provider_name: { hash(connection_key): { "id": "<conn_id>", "created_at": <ts> } } }.
    """

    def __init__(
        self,
        connection_cache_path: (str | Path) | None = None,
    ) -> None:
        self._listening = False
        self._message_handler: Callable[[MessageContext], HandlerResponse] | None = None
        self._connection_cache_path: Path | None = (
            Path(connection_cache_path) if connection_cache_path else None
        )
        # Set by agent when add_provider() is called, or by app for consistent log prefix (e.g. "xwchat: parrot_bot | telegram: ").
        self._agent_id: str | None = None

    def set_agent_id(self, agent_id: str) -> None:
        """Set agent id for log prefix (e.g. 'xwchat: parrot_bot | telegram: '). Called by agent.add_provider() or by app."""
        self._agent_id = agent_id

    def get_connection_id(self, connection_key: str) -> str:
        """Return a stable connection ID for this provider and key. When connection_cache_path is set,
        reads from cache first so the same id is reused after crash/restart (no conflicting connections)."""
        digest = hashlib.sha256(connection_key.encode("utf-8")).hexdigest()
        if self._connection_cache_path is None:
            return f"{self.provider_name}-{digest[:16]}"
        path = self._connection_cache_path
        cache: dict[str, Any] = {}
        if path.exists():
            try:
                cache = JsonSerializer().load_file(path)
            except Exception:
                cache = {}
        providers = cache.setdefault(self.provider_name, {})
        entry = providers.get(digest)
        if isinstance(entry, dict) and "id" in entry:
            conn_id = str(entry["id"])
            _logger.info(
                "Reusing connection id %s from cache for %s (same connection after restart)",
                conn_id,
                self.provider_name,
            )
            return conn_id
        conn_id = f"{self.provider_name}-{int(time.time() * 1000)}"
        providers[digest] = {"id": conn_id, "created_at": time.time()}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            JsonSerializer().save_file(cache, path, indent=2)
        except Exception as e:
            _logger.debug("Could not write connection cache %s: %s", path, e)
        return conn_id

    @property
    def connection_id(self) -> str:
        """Stable connection id; subclasses set _connection_id in __init__."""
        return getattr(self, "_connection_id", "")

    def _log_prefix(self) -> str:
        """Return consistent log prefix: 'xwchat: <agent_id> | <emoji> <provider_name>: ' when agent_id is set, else '<emoji> <provider_name>: '. Optional _provider_emoji reflects provider logo."""
        emoji = getattr(self, "_provider_emoji", "") or ""
        name = f"{emoji} {self.provider_name}".strip() if emoji else self.provider_name
        agent_id = getattr(self, "_agent_id", None)
        if agent_id:
            return f"xwchat: {agent_id} | {name}: "
        return f"{name}: "

    def should_handle_message(self, ctx: MessageContext) -> bool:
        """Return True if the message should be passed to the handler. In groups only when @mentioned; in DMs always; in channels always (bot only receives when admin)."""
        if ctx.get("channel"):
            return True  # Channel: bot only receives when admin; handle all
        if ctx.get("group") and not ctx.get("mentioned"):
            return False
        return True

    def invoke_message_handler(self, ctx: MessageContext) -> HandlerResponse:
        """If should_handle_message(ctx), call the set handler and return response (str, (text, reply_to_id), or None)."""
        if not self.should_handle_message(ctx):
            return None
        if self._message_handler is None:
            return None
        return self._message_handler(ctx)

    @staticmethod
    def _normalize_response(response: HandlerResponse) -> tuple[str | None, str | None, dict[str, Any]]:
        """Return (text, reply_to_message_id, send_kwargs) for sending. Handler may return str, (str, str|None), or (str, str|None, dict)."""
        if response is None:
            return (None, None, {})
        if isinstance(response, tuple):
            text = response[0]
            reply_to = response[1] if len(response) > 1 else None
            kwargs = response[2] if len(response) > 2 else {}
            return (text, reply_to, kwargs)
        return (response, None, {})

    def log_message_received(self, ctx: MessageContext, responded: bool) -> None:
        """Log that a message was received and whether the handler responded. Uses xwsystem logger."""
        group = ctx.get("group", False)
        mentioned = ctx.get("mentioned", False)
        chat_id = ctx.get("chat_id", "?")
        user = ctx.get("username") or ctx.get("user_id", "?")
        text_preview = (ctx.get("text") or "")[:40].replace("\n", " ")
        if len(ctx.get("text") or "") > 40:
            text_preview += "..."
        _logger.info(
            "%schat=%s user=%r group=%s mentioned=%s responded=%s | %r",
            self._log_prefix(),
            chat_id,
            user,
            group,
            mentioned,
            responded,
            text_preview,
        )

    def set_message_handler(
        self,
        handler: Callable[[MessageContext], HandlerResponse],
    ) -> None:
        """Set handler(context) -> response text or None, or (text, reply_to_message_id) to request a reply."""
        self._message_handler = handler

    # ---------- Abstract (REF_12 + parrot) ----------

    @property
    @abstractmethod
    def provider_type(self) -> ChatProviderType:
        """Provider type enum."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[ChatCapability]:
        """Capabilities supported by this provider; gaps are explicit."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the chat service."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        ...

    @abstractmethod
    async def is_connected(self) -> bool:
        """Return True if the provider is connected/ready."""
        ...

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a message to a chat; optionally reply to a specific message."""
        ...

    async def get_message(self, chat_id: str, message_id: str) -> MessageContext | None:
        """Fetch a message by chat and message id. Returns None if not supported or not found. Override when FETCH_MESSAGE_BY_ID capability is set."""
        return None

    @abstractmethod
    async def start_listening(self) -> None:
        """Start receiving messages and dispatching to the message handler. Blocks until stopped."""
        ...


class AChatAgent(IChatAgent, ABC):
    """Abstract base class for chat agent operations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get agent name."""
        ...

    @property
    @abstractmethod
    def title(self) -> str:
        """Get agent title."""
        ...

    @abstractmethod
    def add_provider(self, provider: IChatProvider) -> None:
        """Add a chat provider."""
        ...

    @abstractmethod
    def remove_provider(self, provider_name: str) -> None:
        """Remove a chat provider."""
        ...

    @abstractmethod
    def get_provider(self, provider_name: str) -> IChatProvider | None:
        """Get provider by name."""
        ...

    @abstractmethod
    def list_providers(self) -> list[str]:
        """List all provider names."""
        ...


if __name__ == "__main__":
    print("xwchat.base loaded (AChatProvider, AChatAgent). Run the app with: python -m exonware.xwchat  or  python examples/parrot_bot/hardcoded.py")
