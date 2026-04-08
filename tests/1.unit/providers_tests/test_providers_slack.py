#!/usr/bin/env python3
"""
#exonware/xwchat/tests/1.unit/providers_tests/test_providers_slack.py
Unit tests for SlackChatProvider: _verify_signature.
"""

from __future__ import annotations

import hmac
import hashlib
import time

import pytest

from exonware.xwchat.providers.slack import SlackChatProvider


def test_slack_verify_signature_invalid_timestamp() -> None:
    """_verify_signature returns False for non-numeric timestamp."""
    p = SlackChatProvider("xoxb-test", "secret")
    assert p._verify_signature("not-a-number", b"{}", "v0=abc") is False


def test_slack_verify_signature_old_timestamp() -> None:
    """_verify_signature returns False for timestamp older than 5 min."""
    p = SlackChatProvider("xoxb-test", "secret")
    old_ts = str(int(time.time()) - 400)  # > 5 min ago
    assert p._verify_signature(old_ts, b"{}", "v0=any") is False


def test_slack_verify_signature_valid() -> None:
    """_verify_signature returns True when signature matches."""
    secret = b"my_signing_secret"
    p = SlackChatProvider("xoxb-test", secret.decode("utf-8"))
    ts = str(int(time.time()))
    body = b'{"type":"event_callback"}'
    base = f"v0:{ts}:{body.decode('utf-8')}".encode("utf-8")
    sig = "v0=" + hmac.new(secret, base, hashlib.sha256).hexdigest()
    assert p._verify_signature(ts, body, sig) is True


def test_slack_verify_signature_wrong_signature() -> None:
    """_verify_signature returns False when signature does not match."""
    p = SlackChatProvider("xoxb-test", "secret")
    ts = str(int(time.time()))
    body = b"{}"
    assert p._verify_signature(ts, body, "v0=wrong") is False
