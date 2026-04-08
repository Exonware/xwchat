from collections.abc import AsyncIterator
#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/contracts.py
Protocol interfaces for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

from typing import Any, Protocol, runtime_checkable
from .defs import ChatProviderType, ChatMessageType
@runtime_checkable


class IChatProvider(Protocol):
    """Interface for chat provider operations."""
    @property

    def provider_type(self) -> ChatProviderType:
        """Get provider type."""
        ...
    @property

    def provider_name(self) -> str:
        """Get provider name."""
        ...

    async def send_message(self, user_id: str, text: str, **kwargs) -> Any:
        """Send message to user."""
        ...

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Receive messages from provider (async generator)."""
        ...

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information."""
        ...

    async def user_exists(self, username: str) -> bool:
        """Check if a user exists by username."""
        ...

    async def get_user_id(self, username: str) -> str | None:
        """Get user ID by username."""
        ...

    async def is_connected(self) -> bool:
        """Check if provider is connected."""
        ...

    async def connect(self) -> None:
        """Connect to provider."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from provider."""
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
