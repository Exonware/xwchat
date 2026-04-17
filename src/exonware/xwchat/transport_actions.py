#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/transport_actions.py
``@XWAction`` surface for chat transport controls (e.g. Telegram inbound pause/resume).
Observe the returned agent on :class:`exonware.xwbots.bots.command_bot.XWBotCommand` via ``observe_api_agent``.
Company: eXonware.com
"""

from __future__ import annotations

from typing import Any

from exonware.xwaction import ActionProfile, XWAction
from exonware.xwsystem import get_logger

logger = get_logger(__name__)


class XWChatTelegramTransportAgent:
    """
    Transport-level actions for a :class:`~exonware.xwchat.providers.telegram.TelegramChatProvider`.
    Does not subclass :class:`exonware.xwapi.client.xwclient.XWApiAgent` to keep ``xwchat`` free of an ``xwapi`` dependency.
    """

    _name = "xwchat_telegram"

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def get_actions(self) -> list[Any]:
        return [self.chat_pause, self.chat_resume]

    @XWAction(
        operationId="xwchat.pauseInbound",
        api_name="pause",
        cmd_shortcut="chat_pause",
        summary="Pause Telegram inbound processing (queues non-operator messages)",
        description="Programmatic equivalent of operator /pause on the Telegram transport.",
        profile=ActionProfile.COMMAND,
        tags=["xwchat", "transport"],
        roles=["admin", "owner"],
        audit=True,
    )
    async def chat_pause(self, message: Any = None, context: dict[str, Any] | None = None) -> Any:
        if not hasattr(self._provider, "pause_inbound_processing"):
            return "This chat provider does not support programmatic pause."
        return await self._provider.pause_inbound_processing()

    @XWAction(
        operationId="xwchat.resumeInbound",
        api_name="resume",
        cmd_shortcut="chat_resume",
        summary="Resume Telegram inbound processing and drain the pause queue",
        description="Programmatic equivalent of operator /resume on the Telegram transport.",
        profile=ActionProfile.COMMAND,
        tags=["xwchat", "transport"],
        roles=["admin", "owner"],
        audit=True,
    )
    async def chat_resume(self, message: Any = None, context: dict[str, Any] | None = None) -> Any:
        if not hasattr(self._provider, "resume_inbound_processing"):
            return "This chat provider does not support programmatic resume."
        return await self._provider.resume_inbound_processing()


def observe_telegram_transport_actions(bot: Any, provider: Any, agent_name: str = "xwchat") -> None:
    """Register ``chat_pause`` / ``chat_resume`` on ``bot`` from a Telegram provider instance."""
    observe = getattr(bot, "observe_api_agent", None)
    if not callable(observe):
        logger.warning("observe_telegram_transport_actions: bot has no observe_api_agent (%r)", type(bot).__name__)
        return
    observe(XWChatTelegramTransportAgent(provider), agent_name)
