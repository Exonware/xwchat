#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/defs.py
Type definitions and enums for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.10
Generation Date: 07-Jan-2025
"""

from enum import Enum, auto
from typing import TypedDict


class ChatProviderType(Enum):
    """Chat provider types."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    DISCORD = "discord"
    SLACK = "slack"
    MATRIX = "matrix"
    CUSTOM = "custom"


class ChatCapability(Enum):
    """
    Chat capabilities per REF_12_IDEA §2 and §3.1.
    Providers declare supported capabilities; gaps are explicit.
    """
    IDENTITY_AUTH = auto()
    RECEIVE_MESSAGES = auto()
    SEND_MESSAGES = auto()
    READ_HISTORY = auto()
    ATTACHMENTS = auto()
    THREADS = auto()
    REACTIONS = auto()
    COMMANDS = auto()
    FETCH_MESSAGE_BY_ID = auto()


class MessageContext(TypedDict, total=False):
    """
    Context for an incoming message. Providers fill what they support.
    group: True if message is in a group/supergroup (not DM).
    channel: True if message is a channel post.
    mentioned: True if the bot was @mentioned (used for should_handle_message).
    is_reply: True if this message is a reply to another message (reply_to_message_id is set).
    channel_id: Channel/conversation id (same as chat_id for sending; stored for cache).
    group_id: Guild/server/supergroup id when in a group (Discord: guild id; Telegram: chat id when group).
    """
    chat_id: str
    user_id: str
    text: str
    message_id: str
    reply_to_message_id: str
    is_reply: bool
    thread_id: str
    username: str
    group: bool
    channel: bool
    mentioned: bool
    channel_id: str
    group_id: str
    help_format: str  # e.g. "default", "telegram_markdown_v2" — used by bots to format /help per provider


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
