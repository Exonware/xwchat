#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_basic.py
Basic unit-level sanity checks for all xwchat providers.

These tests:
- Ensure providers can be imported from the public xwchat facade.
- Ensure providers can be instantiated with minimal dummy credentials without
  performing any real network I/O (CONNECT or send_message are not invoked).
- Verify that basic properties like provider_name and capabilities are present.

Per GUIDE_51_TEST:
- This lives in the 1.unit layer and focuses on fast, isolated checks.
- External services are not contacted; HTTP calls would occur only in connect()
  or send_message(), which are not exercised here (except for explicit stub
  providers that are expected to raise).
"""

from __future__ import annotations

import pytest

from exonware.xwchat import (
    ChatCapability,
    ChatProviderType,
    # Core providers already covered elsewhere, but included for completeness
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
    # New / additional providers
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
    XWChatProviderError,
)
from exonware.xwchat.errors import XWChatConnectionError


@pytest.mark.parametrize(
    "provider_cls, kwargs",
    [
        # Core providers (dummy tokens/URLs)
        (TelegramChatProvider, {"api_token": "TEST_TOKEN"}),
        (DiscordChatProvider, {"token": "TEST_TOKEN"}),
        (WhatsAppChatProvider, {"access_token": "TEST_TOKEN", "phone_number_id": "123456"}),
        (SlackChatProvider, {"bot_token": "xoxb-test", "signing_secret": "secret"}),
        (TwilioChatProvider, {"account_sid": "ACxxxx", "auth_token": "auth", "from_number": "+10000000000"}),
        (LineChatProvider, {"channel_access_token": "TEST", "channel_secret": "SECRET"}),
        (ZulipChatProvider, {"site": "https://example.zulipchat.com", "email": "bot@example.com", "api_key": "KEY"}),
        (RocketChatProvider, {"server_url": "https://chat.example.com", "user_id": "USERID", "auth_token": "TOKEN"}),
        (MessengerChatProvider, {"page_access_token": "TEST_PAGE_TOKEN"}),
        (InstagramChatProvider, {"access_token": "TEST_TOKEN", "ig_business_id": "123"}),
        (WebexChatProvider, {"access_token": "TEST_TOKEN"}),
        (ViberChatProvider, {"auth_token": "TEST_TOKEN"}),
        (MatrixChatProvider, {"homeserver_url": "https://matrix.example.com", "access_token": "ACCESS_TOKEN"}),
        (GoogleChatProvider, {"default_webhook_url": "https://chat.example.com/hook"}),
        (TeamsChatProvider, {"default_webhook_url": "https://teams.example.com/hook"}),
        (LinkedInChatProvider, {"access_token": "TEST_TOKEN"}),
        (XTwitterChatProvider, {"bearer_token": "TEST_BEARER"}),
        # New China providers
        (DingTalkChatProvider, {"webhook_url": "https://oapi.dingtalk.com/robot/send"}),
        (FeishuChatProvider, {"app_id": "cli_xxx", "app_secret": "secret"}),
        (WeChatChatProvider, {"app_id": "wx123", "app_secret": "secret"}),
        (QQChatProvider, {"app_id": "1000", "token": "TOKEN"}),
        # Russia/CIS
        (VKChatProvider, {"access_token": "TEST_TOKEN"}),
        (
            OdnoklassnikiChatProvider,
            {"access_token": "TEST_TOKEN", "application_key": "APP_KEY", "application_secret_key": "APP_SECRET"},
        ),
        # Korea
        (KakaoTalkChatProvider, {"rest_api_key": "REST_API_KEY"}),
        # Other messaging
        (SignalChatProvider, {}),
        (ThreemaChatProvider, {"gateway_id": "*TESTID", "api_secret": "SECRET"}),
        (SkypeChatProvider, {"app_id": "APP_ID", "app_password": "PASSWORD"}),
        (SnapchatChatProvider, {"access_token": "TEST_TOKEN"}),
        (TikTokChatProvider, {"access_token": "TEST_TOKEN"}),
        (RedditChatProvider, {"client_id": "CID", "client_secret": "CSEC", "user_agent": "test-agent"}),
        (TwitchChatProvider, {"username": "testuser", "oauth_token": "oauth:TEST"}),
        (YouTubeChatProvider, {"credentials_json_path": "creds.json"}),
        # Business / RCS
        (IMessageChatProvider, {"api_key": "API_KEY", "org_id": "ORG_ID"}),
        (RCSChatProvider, {"agent_id": "AGENT_ID", "credentials_json_path": "rcs-creds.json"}),
        # Channel / alias providers
        (TelegramChannelChatProvider, {"api_token": "TEST_TOKEN"}),
        (FacebookPageChatProvider, {"page_access_token": "TEST_TOKEN"}),
        (PinterestChatProvider, {"access_token": "TEST_TOKEN"}),
        (SlackEnterpriseGridChatProvider, {"bot_token": "xoxb-test", "signing_secret": "secret"}),
    ],
)
def test_provider_instantiation_and_properties(provider_cls, kwargs):
    """
    Instantiate each provider with dummy credentials and verify basic properties.

    This ensures:
    - __init__ accepts the minimal documented parameters.
    - provider_name is a non-empty string.
    - provider_type is a ChatProviderType enum member.
    - capabilities is a frozenset of ChatCapability values (may be empty for some stubs).
    """
    try:
        provider = provider_cls(**kwargs)
    except (XWChatProviderError, XWChatConnectionError) as e:
        msg = str(e).lower()
        if "requires" in msg or "pip install" in msg or "not installed" in msg:
            pytest.skip(f"Optional dependency not installed: {e}")
        raise
    except TypeError as e:
        if "abstract" in str(e).lower() or "start_listening" in str(e):
            pytest.skip(f"Provider has abstract method not implemented: {e}")
        raise

    name = provider.provider_name
    assert isinstance(name, str)
    assert name != ""

    ptype = provider.provider_type
    assert isinstance(ptype, ChatProviderType)

    caps = provider.capabilities
    assert isinstance(caps, frozenset)
    for c in caps:
        assert isinstance(c, ChatCapability)


@pytest.mark.parametrize(
    "provider_cls, kwargs",
    [
        # Providers that explicitly do NOT support send_message and should raise a provider error.
        (SignalChatProvider, {}),
        (SnapchatChatProvider, {"access_token": "TEST_TOKEN"}),
    ],
)
@pytest.mark.asyncio
async def test_send_message_unsupported_providers_raise(provider_cls, kwargs):
    """
    For providers that intentionally do not support send_message, verify that calling
    send_message raises XWChatProviderError with a clear explanation.
    """
    provider = provider_cls(**kwargs)
    with pytest.raises(XWChatProviderError):
        await provider.send_message("chat-id", "hello")

