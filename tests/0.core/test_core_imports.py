#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_imports.py
Test core imports for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

import pytest


def test_import_xwchat_agent():
    """Test importing XWChatAgent."""
    from exonware.xwchat import XWChatAgent
    assert XWChatAgent is not None


def test_import_telegram_provider():
    """Test importing Telegram provider."""
    from exonware.xwchat import Telegram
    assert Telegram is not None


def test_import_interfaces():
    """Test importing interfaces."""
    from exonware.xwchat import IChatAgent, IChatProvider
    assert IChatAgent is not None
    assert IChatProvider is not None


def test_import_abstract_classes():
    """Test importing abstract classes."""
    from exonware.xwchat import AChatAgent, AChatProvider
    assert AChatAgent is not None
    assert AChatProvider is not None


def test_import_defs():
    """Test importing definitions."""
    from exonware.xwchat import ChatProviderType, ChatMessageType
    assert ChatProviderType is not None
    assert ChatMessageType is not None


def test_import_errors():
    """Test importing error classes."""
    from exonware.xwchat import (
        XWChatError,
        XWChatAgentError,
        XWChatProviderError,
        XWChatMessageError,
        XWChatConnectionError,
    )
    assert XWChatError is not None
    assert XWChatAgentError is not None
    assert XWChatProviderError is not None
    assert XWChatMessageError is not None
    assert XWChatConnectionError is not None


def test_import_all_providers_from_facade():
    """Test importing all providers from the public xwchat facade."""
    from exonware.xwchat import (
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
        RCSChatProvider,
        TelegramChannelChatProvider,
        FacebookPageChatProvider,
        PinterestChatProvider,
        SlackEnterpriseGridChatProvider,
    )

    # Just assert they are importable; behavior is covered in unit tests
    assert TelegramChatProvider is not None
    assert DiscordChatProvider is not None
    assert WhatsAppChatProvider is not None
    assert SlackChatProvider is not None
    assert TwilioChatProvider is not None
    assert LineChatProvider is not None
    assert ZulipChatProvider is not None
    assert RocketChatProvider is not None
    assert MessengerChatProvider is not None
    assert InstagramChatProvider is not None
    assert WebexChatProvider is not None
    assert ViberChatProvider is not None
    assert MatrixChatProvider is not None
    assert GoogleChatProvider is not None
    assert TeamsChatProvider is not None
    assert LinkedInChatProvider is not None
    assert XTwitterChatProvider is not None
    assert DingTalkChatProvider is not None
    assert FeishuChatProvider is not None
    assert WeChatChatProvider is not None
    assert QQChatProvider is not None
    assert VKChatProvider is not None
    assert OdnoklassnikiChatProvider is not None
    assert KakaoTalkChatProvider is not None
    assert SignalChatProvider is not None
    assert ThreemaChatProvider is not None
    assert SkypeChatProvider is not None
    assert SnapchatChatProvider is not None
    assert TikTokChatProvider is not None
    assert RedditChatProvider is not None
    assert TwitchChatProvider is not None
    assert YouTubeChatProvider is not None
    assert IMessageChatProvider is not None
    assert RCSChatProvider is not None
    assert TelegramChannelChatProvider is not None
    assert FacebookPageChatProvider is not None
    assert PinterestChatProvider is not None
    assert SlackEnterpriseGridChatProvider is not None
