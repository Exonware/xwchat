#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/facebook_page.py
Facebook Page chat provider using Graph API.

Same as Messenger (Meta); Page Access Token for messaging.
Receiving via webhook; sending via send API.
"""

from __future__ import annotations

from pathlib import Path

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext

from .messenger import MessengerChatProvider

logger = get_logger(__name__)


class FacebookPageChatProvider(MessengerChatProvider):
    """Facebook Page chat provider; alias for Messenger (Meta Graph API)."""

    def __init__(
        self,
        page_access_token: str,
        *,
        connection_cache_path: str | Path | None = None,
    ) -> None:
        super().__init__(
            page_access_token,
            connection_cache_path=connection_cache_path,
        )
        self._provider_emoji = "📘"

    @property
    def provider_name(self) -> str:
        return "facebook_page"
