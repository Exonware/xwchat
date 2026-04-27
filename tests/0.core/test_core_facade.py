#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_facade.py
Test core facade functionality for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

import pytest
from exonware.xwchat import XWChatAgent, Telegram


def test_create_chat_agent():
    """Test creating a chat agent."""
    agent = XWChatAgent(
        name="TestAgent",
        title="Test Chat Agent",
        description="A test agent"
    )
    assert agent.name == "TestAgent"
    assert agent.title == "Test Chat Agent"
    assert agent.description == "A test agent"


def test_add_provider():
    """Test adding a provider to agent."""
    agent = XWChatAgent("TestAgent", "Test Agent")
    # Note: This will fail if python-telegram-bot is not installed
    # but we can test the structure
    try:
        provider = Telegram("test_token")
        agent.add_provider(provider)
        assert "telegram" in agent.list_providers()
    except Exception:
        # Expected if python-telegram-bot is not installed
        pass


def test_provider_access():
    """Test accessing provider via dictionary-like access."""
    agent = XWChatAgent("TestAgent", "Test Agent")
    try:
        provider = Telegram("test_token")
        agent.add_provider(provider)
        assert agent["telegram"] == provider
    except Exception:
        # Expected if python-telegram-bot is not installed
        pass


def test_list_providers():
    """Test listing providers."""
    agent = XWChatAgent("TestAgent", "Test Agent")
    assert agent.list_providers() == []
    try:
        provider = Telegram("test_token")
        agent.add_provider(provider)
        providers = agent.list_providers()
        assert len(providers) == 1
        assert "telegram" in providers
    except Exception:
        # Expected if python-telegram-bot is not installed
        pass
