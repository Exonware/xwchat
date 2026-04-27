#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_invalid_init.py

Negative-path constructor tests for providers.

These tests verify that providers validate required constructor arguments and
raise XWChatProviderError when given obviously invalid credentials, per the
defensive checks implemented in each provider.

No network I/O is performed; we only exercise __init__ validation logic.
"""

from __future__ import annotations

import pytest

from exonware.xwchat import (
    XWChatProviderError,
    DingTalkChatProvider,
    FeishuChatProvider,
    WeChatChatProvider,
    QQChatProvider,
    VKChatProvider,
    OdnoklassnikiChatProvider,
    KakaoTalkChatProvider,
    SnapchatChatProvider,
    TikTokChatProvider,
    RedditChatProvider,
    TwitchChatProvider,
    IMessageChatProvider,
    RCSChatProvider,
    PinterestChatProvider,
    SlackEnterpriseGridChatProvider,
)


@pytest.mark.parametrize(
    "provider_cls, kwargs",
    [
        (DingTalkChatProvider, {"webhook_url": ""}),
        (FeishuChatProvider, {"app_id": "", "app_secret": ""}),
        (WeChatChatProvider, {"app_id": "", "app_secret": ""}),
        (QQChatProvider, {"app_id": "", "token": ""}),
        (VKChatProvider, {"access_token": ""}),
        (
            OdnoklassnikiChatProvider,
            {"access_token": "", "application_key": "", "application_secret_key": ""},
        ),
        (KakaoTalkChatProvider, {"rest_api_key": ""}),
        (SnapchatChatProvider, {"access_token": ""}),
        (TikTokChatProvider, {"access_token": ""}),
        (
            RedditChatProvider,
            {"client_id": "", "client_secret": "", "user_agent": ""},
        ),
        (TwitchChatProvider, {"username": "", "oauth_token": ""}),
        (IMessageChatProvider, {"api_key": "", "org_id": ""}),
        (RCSChatProvider, {"agent_id": ""}),
        (PinterestChatProvider, {"access_token": ""}),
        (
            SlackEnterpriseGridChatProvider,
            {"bot_token": "", "signing_secret": ""},
        ),
    ],
)
def test_invalid_constructor_arguments_raise(provider_cls, kwargs):
    """
    When clearly invalid credentials are provided, providers should raise
    XWChatProviderError from __init__ instead of silently accepting them.
    """
    with pytest.raises(XWChatProviderError):
        provider_cls(**kwargs)

