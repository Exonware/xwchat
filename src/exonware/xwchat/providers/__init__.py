#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/__init__.py
Chat providers package.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.9
Generation Date: 07-Jan-2025
"""
from .telegram import TelegramChatProvider, Telegram, user_exists
from .discord import DiscordChatProvider, Discord
from .whatsapp import WhatsAppChatProvider, WhatsApp
from .slack import SlackChatProvider
from .twilio import TwilioChatProvider
from .line import LineChatProvider
from .zulip import ZulipChatProvider
from .rocketchat import RocketChatProvider
from .messenger import MessengerChatProvider
from .instagram import InstagramChatProvider
from .webex import WebexChatProvider
from .viber import ViberChatProvider
from .matrix import MatrixChatProvider
from .google_chat import GoogleChatProvider
from .teams import TeamsChatProvider
from .linkedin import LinkedInChatProvider
from .x_twitter import XTwitterChatProvider
from .dingtalk import DingTalkChatProvider
from .feishu import FeishuChatProvider, LarkChatProvider
from .wechat import WeChatChatProvider
from .qq import QQChatProvider
from .vk import VKChatProvider
from .odnoklassniki import OdnoklassnikiChatProvider
from .kakaotalk import KakaoTalkChatProvider
from .signal import SignalChatProvider
from .threema import ThreemaChatProvider
from .skype import SkypeChatProvider
from .snapchat import SnapchatChatProvider
from .tiktok import TikTokChatProvider
from .reddit import RedditChatProvider
from .twitch import TwitchChatProvider
from .youtube import YouTubeChatProvider
from .imessage import IMessageChatProvider, AppleBusinessChatProvider
from .rcs import RCSChatProvider
from .telegram_channel import TelegramChannelChatProvider
from .facebook_page import FacebookPageChatProvider
from .pinterest import PinterestChatProvider
from .slack_enterprise import SlackEnterpriseGridChatProvider

__all__ = [
    # New naming-convention classes
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
    # Utilities
    "user_exists",
]
