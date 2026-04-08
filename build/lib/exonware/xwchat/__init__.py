#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/__init__.py
XWChat Package Initialization
This module provides chat agent framework for the eXonware ecosystem.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
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
# Core exports
from .agent import XWChatAgent
from .contracts import (
    IChatAgent, IChatProvider
)
from .base import (
    AChatAgent, AChatProvider
)
from .defs import (
    ChatProviderType, ChatMessageType
)
from .errors import (
    XWChatError, XWChatAgentError, XWChatProviderError,
    XWChatMessageError, XWChatConnectionError
)
# Provider exports
from .providers import Telegram
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Main classes
    "XWChatAgent",
    # Interfaces
    "IChatAgent",
    "IChatProvider",
    # Abstract classes
    "AChatAgent",
    "AChatProvider",
    # Definitions
    "ChatProviderType",
    "ChatMessageType",
    # Errors
    "XWChatError",
    "XWChatAgentError",
    "XWChatProviderError",
    "XWChatMessageError",
    "XWChatConnectionError",
    # Providers
    "Telegram",
]
