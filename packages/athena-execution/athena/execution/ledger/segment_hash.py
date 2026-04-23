"""Monthly segment-hash computation for pre_trade_ledger.

Source-of-truth: Story 1.5 AC-3 / §Invariant #6.

The segment hash is the chain-of-custody link between months. Empty months
are fully represented — a month with zero entries still emits a segment
hash of `SHA256(prev_segment_hash || SHA256(b"") || policy_version_git_sha)`,
so a downstream audit can never mistake "no trades" for "month missing from
the chain".

The canonical form (concatenation order + separator) is part of the spec —
Story 6.2 's three-way verify job re-runs `compute_segment_hash` against the
same inputs and the reference JSON stored on the external SSD + S3 Object
Lock bucket. Any drift here would silently break the verify job.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass(frozen=True)
class SegmentHashResult:
    """Record shape for `scripts/monthly_ledger_chain.py` JSON output.

    Frozen to guarantee callers cannot mutate a result after computing it
    (Story 6.2 's verify job compares results across systems byte-for-byte)."""

    month: str  # "YYYY-MM"
    segment_hash: str  # 64-char hex
    prev_segment_hash: str | None  # None for the very first segment ever
    entry_count: int
    first_id: int | None
    last_id: int | None
    computed_at_utc: str  # ISO 8601


def compute_segment_hash(
    conn: duckdb.DuckDBPyConnection,
    *,
    year: int,
    month: int,
    prev_segment_hash: str | None,
    policy_version_git_sha: str,
) -> SegmentHashResult:
    """Compute the segment_hash for the month [year-month-01, year-month+1-01).

    segment_hash  = SHA256(prev_segment_hash || sorted_ids_hash
                           || policy_version_git_sha)
    sorted_ids_hash = SHA256("\\n".join(str(id) for id in ids))
                     when the month is non-empty, else SHA256(b"").

    Ordering: the SQL query appends `ORDER BY id` so `ids` arrives sorted
    ascending — the hash input therefore matches "sorted(ids)" without a
    Python-side `sorted()` call.

    Separator for the outer hash input is `\\x00`. By construction the
    inputs are: (a) either empty or 64-char lowercase hex (`prev_segment_hash`),
    (b) 64-char hex (`sorted_ids_hash`), (c) 40-char hex
    (`policy_version_git_sha`) — none of which can contain a raw NUL, so the
    concatenation is unambiguous without length prefixes. See
    `hash_chain.py` module docstring for the broader argument.
    """
    # Month+1 with December → Jan of next year.
    next_year = year + (1 if month == 12 else 0)
    next_month = 1 if month == 12 else month + 1
    # `created_at_utc` is TIMESTAMPTZ. `make_timestamp` returns a naive
    # TIMESTAMP which DuckDB would coerce using the session timezone — on a
    # Trading PC running KST that silently shifts the month boundary by 9h.
    # Anchor the bucket to UTC by casting the literal to TIMESTAMPTZ with
    # `AT TIME ZONE 'UTC'` so the comparison is timezone-invariant.
    rows = conn.execute(
        "SELECT id FROM pre_trade_ledger "
        "WHERE created_at_utc >= make_timestamp(?, ?, 1, 0, 0, 0.0) AT TIME ZONE 'UTC' "
        "AND created_at_utc <  make_timestamp(?, ?, 1, 0, 0, 0.0) AT TIME ZONE 'UTC' "
        "ORDER BY id",
        [year, month, next_year, next_month],
    ).fetchall()
    ids = [int(r[0]) for r in rows]
    if ids:
        sorted_ids_hash = hashlib.sha256("\n".join(str(i) for i in ids).encode("ascii")).hexdigest()
    else:
        sorted_ids_hash = hashlib.sha256(b"").hexdigest()
    body = "\x00".join(
        [
            prev_segment_hash or "",
            sorted_ids_hash,
            policy_version_git_sha,
        ]
    ).encode("utf-8")
    segment_hash = hashlib.sha256(body).hexdigest()
    return SegmentHashResult(
        month=f"{year:04d}-{month:02d}",
        segment_hash=segment_hash,
        prev_segment_hash=prev_segment_hash,
        entry_count=len(ids),
        first_id=ids[0] if ids else None,
        last_id=ids[-1] if ids else None,
        computed_at_utc=datetime.now(UTC).isoformat(),
    )


__all__ = ["SegmentHashResult", "compute_segment_hash"]
