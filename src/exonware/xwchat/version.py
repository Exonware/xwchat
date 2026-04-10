#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/version.py
Version information for xwchat.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.4
Generation Date: 07-Jan-2025
"""

from datetime import datetime


def _today_release_date() -> str:
    """Return today's date in DD-MMM-YYYY."""
    return datetime.now().strftime("%d-%b-%Y")
__version__ = "0.0.1.4"
# Release/update date (DD-MMM-YYYY). Evaluated at import time.
__date__ = _today_release_date()
__author__ = "eXonware Backend Team"
__email__ = "connect@exonware.com"


def get_date() -> str:
    """Get the release/update date (DD-MMM-YYYY)."""
    return __date__
