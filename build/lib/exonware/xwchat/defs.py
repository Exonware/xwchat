#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/defs.py
Type definitions and enums for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

from enum import Enum
from typing import Any


class ChatProviderType(Enum):
    """Chat provider types."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    DISCORD = "discord"
    SLACK = "slack"
    CUSTOM = "custom"


class ChatMessageType(Enum):
    """Chat message types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    VOICE = "voice"
    LOCATION = "location"
    CONTACT = "contact"
