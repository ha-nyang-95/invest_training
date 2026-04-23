"""S3 Object Lock Compliance config + object-key SSOT for ledger backup.

Source-of-truth: Story 1.5 AC-5 / §Invariant #8.

`object_key_for_segment` is the single source of truth for the S3 key layout.
Story 6.2's verify job and Story 1.10's backup automation BOTH import this
function — never hand-format the key string. The layout matches Parquet
hive-partition conventions (year=YYYY/month=MM) so any prefix-scan / S3
Select tool already familiar with the market-data lake works here too.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectLockConfig:
    """Frozen snapshot of the Object Lock bucket configuration.

    V1.0 pins `mode="COMPLIANCE"` — Governance mode allows bypass by the
    root account, which violates NFR-A2 (영구 보존). If a future story needs
    Governance (e.g. staging env), add a separate factory function rather
    than mutating this default.
    """

    bucket: str
    region: str
    retention_years: int = 5
    mode: str = "COMPLIANCE"


def object_key_for_segment(*, user_id: int, year: int, month: int) -> str:
    """Deterministic S3 object key for the monthly segment-hash JSON.

    Format: `ledger/user_id=<N>/year=YYYY/month=MM/segment_hash.json`

    Month is zero-padded to 2 digits so lexicographic sort matches calendar
    order, matching the external-SSD layout written by
    `scripts/monthly_ledger_chain.py --out-local`.
    """
    return f"ledger/user_id={user_id}/year={year:04d}/month={month:02d}/segment_hash.json"


__all__ = ["ObjectLockConfig", "object_key_for_segment"]
