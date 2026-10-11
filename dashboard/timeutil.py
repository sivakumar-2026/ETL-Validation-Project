"""IST timestamps for reports."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist_label() -> str:
    """e.g. 11 Oct 2026, 12:17:13 IST"""
    return datetime.now(IST).strftime("%d %b %Y, %H:%M:%S IST")


def now_ist_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")
