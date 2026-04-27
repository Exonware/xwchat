#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_agent.py
Tests for XWChatAgent: init, add/remove provider, get/list, dict-like access, fluent API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from exonware.xwchat import (
    XWChatAgent,
    AChatProvider,
    IChatAgent,
    IChatProvider,
    XWChatAgentError,
)
from exonware.xwchat.providers.dingtalk import DingTalkChatProvider


@pytest.fixture
def agent() -> XWChatAgent:
    return XWChatAgent(name="TestAgent", title="Test Agent", description="Test")


@pytest.fixture
def provider() -> DingTalkChatProvider:
    return DingTalkChatProvider("https://example.com/hook")


def test_agent_name_title_description(agent: XWChatAgent) -> None:
    assert agent.name == "TestAgent"
    assert agent.title == "Test Agent"
    assert agent.description == "Test"


def test_agent_agent_id(agent: XWChatAgent) -> None:
    assert agent.agent_id == "TestAgent"


def test_agent_data_path(agent: XWChatAgent) -> None:
    assert isinstance(agent.data_path, Path)
    assert "xwchat" in str(agent.data_path).replace("\\", "/").lower()


def test_agent_data_path_custom() -> None:
    a = XWChatAgent("A", data_path="/custom/path")
    assert a.data_path == Path("/custom/path")


def test_agent_metadata(agent: XWChatAgent) -> None:
    assert agent.metadata == {}
    a2 = XWChatAgent("A", title="T", extra="value")
    assert a2.metadata.get("extra") == "value"


def test_agent_list_providers_empty(agent: XWChatAgent) -> None:
    assert agent.list_providers() == []


def test_agent_add_provider(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    agent.add_provider(provider)
    assert agent.list_providers() == ["dingtalk"]
    assert agent.get_provider("dingtalk") is provider


def test_agent_add_provider_replaces(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    agent.add_provider(provider)
    p2 = DingTalkChatProvider("https://other.com/hook")
    agent.add_provider(p2)
    assert agent.get_provider("dingtalk") is p2


def test_agent_add_provider_invalid_type_raises(agent: XWChatAgent) -> None:
    with pytest.raises(XWChatAgentError):
        agent.add_provider("not a provider")  # type: ignore[arg-type]
    # Object without protocol attributes should fail isinstance(IChatProvider)
    class NotAProvider:
        pass
    with pytest.raises(XWChatAgentError):
        agent.add_provider(NotAProvider())  # type: ignore[arg-type]


def test_agent_remove_provider(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    agent.add_provider(provider)
    agent.remove_provider("dingtalk")
    assert agent.list_providers() == []
    assert agent.get_provider("dingtalk") is None


def test_agent_remove_provider_missing_no_raise(agent: XWChatAgent) -> None:
    agent.remove_provider("nonexistent")


def test_agent_get_provider(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    agent.add_provider(provider)
    assert agent.get_provider("dingtalk") is provider
    assert agent.get_provider("missing") is None


def test_agent_getitem(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    agent.add_provider(provider)
    assert agent["dingtalk"] is provider
    with pytest.raises(XWChatAgentError):
        _ = agent["missing"]


def test_agent_contains(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    assert "dingtalk" not in agent
    agent.add_provider(provider)
    assert "dingtalk" in agent


def test_agent_len(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    assert len(agent) == 0
    agent.add_provider(provider)
    assert len(agent) == 1


def test_agent_providers_fluent(agent: XWChatAgent) -> None:
    from exonware.xwchat.providers.teams import TeamsChatProvider
    p1 = DingTalkChatProvider("https://example.com/hook1")
    p2 = TeamsChatProvider(default_webhook_url="https://teams.example.com/hook")
    result = agent.providers(p1, p2)
    assert result is agent
    assert len(agent) == 2
    assert "dingtalk" in agent.list_providers()
    assert "teams" in agent.list_providers()


def test_agent_repr(agent: XWChatAgent, provider: DingTalkChatProvider) -> None:
    r = repr(agent)
    assert "TestAgent" in r
    assert "Test Agent" in r
    agent.add_provider(provider)
    r2 = repr(agent)
    assert "1" in r2


def test_agent_implements_IChatAgent(agent: XWChatAgent) -> None:
    assert isinstance(agent, IChatAgent)


def test_agent_storage_connection_default(agent: XWChatAgent) -> None:
    assert agent.storage_connection is None


def test_agent_auth_default(agent: XWChatAgent) -> None:
    assert agent.auth is None
