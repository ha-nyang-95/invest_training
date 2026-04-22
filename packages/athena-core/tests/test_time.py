"""Unit tests for athena.core.time: strict input-tz enforcement (P-10).

Review-origin (bmad-code-review 2026-04-21): `kst_to_utc` / `utc_to_kst` previously
accepted any tz-aware input and silently treated it as the named source tz — a
misuse trap. Now they verify the utcoffset matches the function's source semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from athena.core.time import kst_to_utc, utc_to_kst


def test_kst_to_utc_round_trips_nine_hour_offset() -> None:
    kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    utc = kst_to_utc(kst)
    assert utc == datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)


def test_utc_to_kst_round_trips_nine_hour_offset() -> None:
    utc = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)
    kst = utc_to_kst(utc)
    assert kst.utcoffset() == timedelta(hours=9)
    assert kst.hour == 21


def test_kst_to_utc_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive input forbidden"):
        kst_to_utc(datetime(2026, 4, 21, 21, 0, 0))  # noqa: DTZ001


def test_utc_to_kst_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive input forbidden"):
        utc_to_kst(datetime(2026, 4, 21, 12, 0, 0))  # noqa: DTZ001


def test_kst_to_utc_rejects_wrong_tz() -> None:
    # America/New_York has offset != +09:00 — must be rejected, not silently re-labelled.
    ny = datetime(2026, 4, 21, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with pytest.raises(ValueError, match="Asia/Seoul"):
        kst_to_utc(ny)


def test_utc_to_kst_rejects_wrong_tz() -> None:
    # Even UTC+01:00 (not UTC) must be rejected; caller should convert first.
    paris = datetime(2026, 4, 21, 13, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(ValueError, match="UTC"):
        utc_to_kst(paris)
