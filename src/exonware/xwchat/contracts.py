#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/contracts.py
Protocol interfaces for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.8
Generation Date: 07-Jan-2025
"""

from typing import Any, Callable, Protocol, runtime_checkable

from .defs import ChatCapability, ChatProviderType, MessageContext

# Handler may return text only, (text, reply_to_message_id), or (text, reply_to_message_id, send_kwargs) for provider-specific send options (e.g. parse_mode).
HandlerResponse = str | tuple[str, str | None] | tuple[str, str | None, dict[str, Any]] | None


@runtime_checkable
class IChatProvider(Protocol):
    """
    Interface for chat providers.
    Covers REF_12_IDEA §2 (identity, receive, send, history, attachments, etc.)
    and parrot_bot surface (message handler, start_listening, connection_id).
    """

    @property
    def provider_type(self) -> ChatProviderType:
        """Provider type enum."""
        ...

    @property
    def provider_name(self) -> str:
        """Stable provider identifier (e.g. 'telegram', 'discord')."""
        ...

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        """Capabilities supported by this provider; gaps are explicit (REF_12 §3.2)."""
        ...

    @property
    def connection_id(self) -> str:
        """Stable connection id for this provider instance."""
        ...

    def get_connection_id(self, connection_key: str) -> str:
        """Return a stable connection ID for the given key (e.g. token)."""
        ...

    def set_message_handler(
        self,
        handler: Callable[[MessageContext], HandlerResponse],
    ) -> None:
        """Set handler(context) -> response text or None, or (text, reply_to_message_id) to request a reply."""
        ...

    def should_handle_message(self, ctx: MessageContext) -> bool:
        """Return True if the message should be passed to the handler (e.g. in groups only when @mentioned)."""
        ...

    def invoke_message_handler(self, ctx: MessageContext) -> HandlerResponse:
        """If should_handle_message(ctx), call the set handler and return response; else None."""
        ...

    def log_message_received(self, ctx: MessageContext, responded: bool) -> None:
        """Log that a message was received and whether the handler responded."""
        ...

    async def connect(self) -> None:
        """Establish connection to the chat service."""
        ...

    async def disconnect(self) -> None:
        """Close connection."""
        ...

    async def is_connected(self) -> bool:
        """Return True if the provider is connected/ready."""
        ...

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
        """Fetch a message by chat and message id. Returns None if not supported or not found. Only supported when FETCH_MESSAGE_BY_ID capability is set."""
        ...

    async def start_listening(self) -> None:
        """Start receiving messages and dispatching to the message handler. Blocks until stopped."""
        ...


@runtime_checkable
class IChatAgent(Protocol):
    """Interface for chat agent operations."""

    @property
    def name(self) -> str:
        """Get agent name."""
        ...

    @property
    def title(self) -> str:
        """Get agent title."""
        ...

    def add_provider(self, provider: IChatProvider) -> None:
        """Add a chat provider."""
        ...

    def remove_provider(self, provider_name: str) -> None:
        """Remove a chat provider."""
        ...

    def get_provider(self, provider_name: str) -> IChatProvider | None:
        """Get provider by name."""
        ...

    def list_providers(self) -> list[str]:
        """List all provider names."""
        ...
