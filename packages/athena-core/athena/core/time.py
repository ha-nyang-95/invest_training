"""Timezone utilities — Asia/Seoul ↔ UTC.

Stub for downstream stories (DTO timestamp validators, KIS API time
serialization). Naive datetime is forbidden everywhere; both helpers raise
ValueError on naive input per Enforcement #6.

Input tz must match the function's source semantics:
- `kst_to_utc` requires the input to be in Asia/Seoul (utcoffset == +09:00).
- `utc_to_kst` requires the input to be UTC (utcoffset == 0).
This guards against misuse where callers pass an arbitrary tz-aware value
expecting the function to treat it as the named source.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")
_UTC = ZoneInfo("UTC")
_KST_OFFSET = timedelta(hours=9)


def kst_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("kst_to_utc requires timezone-aware datetime; naive input forbidden")
    if dt.utcoffset() != _KST_OFFSET:
        raise ValueError(
            f"kst_to_utc expects Asia/Seoul input (+09:00); got utcoffset={dt.utcoffset()!r}"
        )
    return dt.astimezone(_UTC)


def utc_to_kst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("utc_to_kst requires timezone-aware datetime; naive input forbidden")
    if dt.utcoffset() != timedelta(0):
        raise ValueError(
            f"utc_to_kst expects UTC input (offset 0); got utcoffset={dt.utcoffset()!r}"
        )
    return dt.astimezone(_KST)
