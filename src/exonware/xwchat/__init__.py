#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/__init__.py
XWChat Package Initialization
This module provides chat agent framework for the eXonware ecosystem.
Logging: uses exonware.xwsystem get_logger (all loggers under exonware.xwchat).
Enable/disable: set env XWCHAT_LOGGING_ENABLED=false to disable, or XWCHAT_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|0;
or use enable_xwchat_logging() / disable_xwchat_logging() / set_xwchat_log_level() in code.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.10
Generation Date: 07-Jan-2025
"""
# =============================================================================
# XWLAZY INTEGRATION - Auto-install missing dependencies silently (EARLY)
# =============================================================================
# Activate xwlazy BEFORE other imports to enable auto-installation of missing dependencies
# This enables silent auto-installation of missing libraries when they are imported

try:
    from exonware.xwlazy import auto_enable_lazy
    auto_enable_lazy(__package__ or "exonware.xwchat", mode="smart")
except ImportError:
    # xwlazy not installed - lazy mode simply stays disabled (normal behavior)
    pass
from .version import __version__, __author__, __email__
# Standard imports - NO try/except!
from exonware.xwsystem import get_logger
# Apply xwchat logging from env (XWCHAT_LOGGING_ENABLED, XWCHAT_LOG_LEVEL); reuses xwsystem logging
from .logging_config import (
    apply_xwchat_logging_from_env,
    set_xwchat_log_level,
    enable_xwchat_logging,
    disable_xwchat_logging,
    is_xwchat_logging_enabled,
)
apply_xwchat_logging_from_env()
# Core exports
from .agent import XWChatAgent
from .contracts import (
    IChatAgent, IChatProvider
)
from .base import (
    AChatAgent, AChatProvider
)
from .defs import (
    ChatCapability,
    ChatMessageType,
    ChatProviderType,
    MessageContext,
)
from .errors import (
    XWChatError, XWChatAgentError, XWChatProviderError,
    XWChatMessageError, XWChatConnectionError
)
# Provider exports
from .providers import (
    TelegramChatProvider,
    DiscordChatProvider,
    WhatsAppChatProvider,
    SlackChatProvider,
    TwilioChatProvider,
    LineChatProvider,
    ZulipChatProvider,
    RocketChatProvider,
    MessengerChatProvider,
    InstagramChatProvider,
    WebexChatProvider,
    ViberChatProvider,
    MatrixChatProvider,
    GoogleChatProvider,
    TeamsChatProvider,
    LinkedInChatProvider,
    XTwitterChatProvider,
    DingTalkChatProvider,
    FeishuChatProvider,
    LarkChatProvider,
    WeChatChatProvider,
    QQChatProvider,
    VKChatProvider,
    OdnoklassnikiChatProvider,
    KakaoTalkChatProvider,
    SignalChatProvider,
    ThreemaChatProvider,
    SkypeChatProvider,
    SnapchatChatProvider,
    TikTokChatProvider,
    RedditChatProvider,
    TwitchChatProvider,
    YouTubeChatProvider,
    IMessageChatProvider,
    AppleBusinessChatProvider,
    RCSChatProvider,
    TelegramChannelChatProvider,
    FacebookPageChatProvider,
    PinterestChatProvider,
    SlackEnterpriseGridChatProvider,
    # Backwards-compatible aliases
    Telegram,
    Discord,
    WhatsApp,
)
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Logging (xwsystem get_logger + xwchat enable/disable)
    "get_logger",
    "set_xwchat_log_level",
    "enable_xwchat_logging",
    "disable_xwchat_logging",
    "is_xwchat_logging_enabled",
    # Main classes
    "XWChatAgent",
    # Interfaces
    "IChatAgent",
    "IChatProvider",
    # Abstract classes
    "AChatAgent",
    "AChatProvider",
    # Definitions
    "ChatCapability",
    "ChatMessageType",
    "ChatProviderType",
    "MessageContext",
    # Errors
    "XWChatError",
    "XWChatAgentError",
    "XWChatProviderError",
    "XWChatMessageError",
    "XWChatConnectionError",
    # Providers (new naming convention)
    "TelegramChatProvider",
    "DiscordChatProvider",
    "WhatsAppChatProvider",
    "SlackChatProvider",
    "TwilioChatProvider",
    "LineChatProvider",
    "ZulipChatProvider",
    "RocketChatProvider",
    "MessengerChatProvider",
    "InstagramChatProvider",
    "WebexChatProvider",
    "ViberChatProvider",
    "MatrixChatProvider",
    "GoogleChatProvider",
    "TeamsChatProvider",
    "LinkedInChatProvider",
    "XTwitterChatProvider",
    "DingTalkChatProvider",
    "FeishuChatProvider",
    "LarkChatProvider",
    "WeChatChatProvider",
    "QQChatProvider",
    "VKChatProvider",
    "OdnoklassnikiChatProvider",
    "KakaoTalkChatProvider",
    "SignalChatProvider",
    "ThreemaChatProvider",
    "SkypeChatProvider",
    "SnapchatChatProvider",
    "TikTokChatProvider",
    "RedditChatProvider",
    "TwitchChatProvider",
    "YouTubeChatProvider",
    "IMessageChatProvider",
    "AppleBusinessChatProvider",
    "RCSChatProvider",
    "TelegramChannelChatProvider",
    "FacebookPageChatProvider",
    "PinterestChatProvider",
    "SlackEnterpriseGridChatProvider",
    # Backwards-compatible aliases
    "Telegram",
    "Discord",
    "WhatsApp",
]
