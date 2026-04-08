from collections.abc import AsyncIterator
#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/base.py
Abstract base classes for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

from abc import ABC, abstractmethod
from typing import Any
from .contracts import IChatAgent, IChatProvider
from .defs import ChatProviderType, ChatMessageType


class AChatProvider(IChatProvider, ABC):
    """Abstract base class for chat provider operations."""
    @property
    @abstractmethod

    def provider_type(self) -> ChatProviderType:
        """Get provider type."""
        pass
    @property
    @abstractmethod

    def provider_name(self) -> str:
        """Get provider name."""
        pass
    @abstractmethod

    async def send_message(self, user_id: str, text: str, **kwargs) -> Any:
        """Send message to user."""
        pass
    @abstractmethod

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Receive messages from provider (async generator)."""
        pass
    @abstractmethod

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information."""
        pass
    @abstractmethod

    async def user_exists(self, username: str) -> bool:
        """Check if a user exists by username."""
        pass
    @abstractmethod

    async def get_user_id(self, username: str) -> str | None:
        """Get user ID by username."""
        pass
    @abstractmethod

    async def is_connected(self) -> bool:
        """Check if provider is connected."""
        pass
    @abstractmethod

    async def connect(self) -> None:
        """Connect to provider."""
        pass
    @abstractmethod

    async def disconnect(self) -> None:
        """Disconnect from provider."""
        pass


class AChatAgent(IChatAgent, ABC):
    """Abstract base class for chat agent operations."""
    @property
    @abstractmethod

    def name(self) -> str:
        """Get agent name."""
        pass
    @property
    @abstractmethod

    def title(self) -> str:
        """Get agent title."""
        pass
    @abstractmethod

    def add_provider(self, provider: IChatProvider) -> None:
        """Add a chat provider."""
        pass
    @abstractmethod

    def remove_provider(self, provider_name: str) -> None:
        """Remove a chat provider."""
        pass
    @abstractmethod

    def get_provider(self, provider_name: str) -> IChatProvider | None:
        """Get provider by name."""
        pass
    @abstractmethod

    def list_providers(self) -> list[str]:
        """List all provider names."""
        pass
