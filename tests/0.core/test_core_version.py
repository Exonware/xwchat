#!/usr/bin/env python3
"""
#exonware/xwchat/tests/0.core/test_core_version.py
Tests for version module: __version__, __date__, get_date, __author__, __email__.
"""

from __future__ import annotations

import re

import pytest

from exonware.xwchat.version import (
    __version__,
    __date__,
    __author__,
    __email__,
    get_date,
    _today_release_date,
)


def test_version_format() -> None:
    assert isinstance(__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+\.\d+$", __version__), "expected 0.0.1.0 style"


def test_date_format() -> None:
    assert isinstance(__date__, str)
    assert re.match(r"^\d{2}-[A-Za-z]{3}-\d{4}$", __date__), "expected DD-MMM-YYYY"


def test_get_date_returns_date() -> None:
    assert get_date() == __date__


def test_today_release_date_format() -> None:
    s = _today_release_date()
    assert re.match(r"^\d{2}-[A-Za-z]{3}-\d{4}$", s)


def test_author() -> None:
    assert isinstance(__author__, str)
    assert len(__author__) > 0


def test_email() -> None:
    assert isinstance(__email__, str)
    assert "@" in __email__
