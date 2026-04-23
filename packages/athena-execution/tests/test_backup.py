"""Story 1.5 Task 5.4 — backup.py unit scenarios (AC-5 "Then").

Stage-2 (no marker) — pure-Python checks against `object_key_for_segment`
and `ObjectLockConfig`.
"""

from __future__ import annotations

import dataclasses

import pytest
from athena.execution.ledger.backup import ObjectLockConfig, object_key_for_segment


def test_object_key_format_matches_epics_spec() -> None:
    """epics.md line 585 pins the exact key layout — any drift here breaks
    Story 6.2 's verify job (S3 ↔ local SSD ↔ DB three-way compare)."""
    key = object_key_for_segment(user_id=1, year=2026, month=4)
    assert key == "ledger/user_id=1/year=2026/month=04/segment_hash.json"


def test_object_key_month_zero_pads() -> None:
    # March → 03, December → 12. Ensures lexicographic sort = calendar order.
    assert object_key_for_segment(user_id=1, year=2026, month=3).endswith(
        "month=03/segment_hash.json"
    )
    assert object_key_for_segment(user_id=1, year=2026, month=12).endswith(
        "month=12/segment_hash.json"
    )


def test_object_lock_config_is_frozen() -> None:
    cfg = ObjectLockConfig(bucket="test", region="ap-northeast-2")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.retention_years = 10  # type: ignore[misc]


def test_object_lock_config_defaults() -> None:
    cfg = ObjectLockConfig(bucket="test", region="ap-northeast-2")
    # NFR-A2 영구 보존 → COMPLIANCE must be the default, not GOVERNANCE.
    assert cfg.mode == "COMPLIANCE"
    # D6: minimum 5 years retention.
    assert cfg.retention_years == 5
