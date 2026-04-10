#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/errors.py
Error classes for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.5
Generation Date: 07-Jan-2025
"""


class XWChatError(Exception):
    """Base error for xwchat."""
    pass


class XWChatAgentError(XWChatError):
    """Chat agent-related errors."""
    pass


class XWChatProviderError(XWChatError):
    """Chat provider-related errors."""
    pass


class XWChatMessageError(XWChatError):
    """Chat message-related errors."""
    pass


class XWChatConnectionError(XWChatProviderError):
    """Chat connection-related errors."""
    pass
