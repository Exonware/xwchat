#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/slack_enterprise.py
Slack Enterprise Grid chat provider.

Same as SlackChatProvider but for Enterprise Grid orgs.
Uses org-level token; same Events API + Web API.
"""

from __future__ import annotations

from exonware.xwsystem import get_logger

from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext

from .slack import SlackChatProvider

logger = get_logger(__name__)


class SlackEnterpriseGridChatProvider(SlackChatProvider):
    """Slack Enterprise Grid provider; same API as Slack with org-level token."""

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        *,
        webhook_port: int = 3000,
        webhook_path: str = "/slack/events",
        connection_cache_path: str | None = None,
    ) -> None:
        super().__init__(
            bot_token,
            signing_secret,
            webhook_port=webhook_port,
            webhook_path=webhook_path,
            connection_cache_path=connection_cache_path,
        )
        self._provider_emoji = "🏢"

    @property
    def provider_name(self) -> str:
        return "slack_enterprise_grid"
