"""Timezone utilities — Asia/Seoul ↔ UTC.

Stub for downstream stories (DTO timestamp validators, KIS API time
serialization). Naive datetime is forbidden everywhere; both helpers raise
ValueError on naive input per Enforcement #6.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")
_UTC = ZoneInfo("UTC")


def kst_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("kst_to_utc requires timezone-aware datetime; naive input forbidden")
    return dt.astimezone(_UTC)


def utc_to_kst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("utc_to_kst requires timezone-aware datetime; naive input forbidden")
    return dt.astimezone(_KST)
