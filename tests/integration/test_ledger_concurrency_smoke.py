"""Story 1.5 Task 2.4 — asyncio cooperative append smoke + multi-connection
skip marker.

Stage-3 integration (`@pytest.mark.integration`).

V1.0 concurrency model (architecture.md D13): single asyncio loop + single
DuckDB connection. asyncio tasks running `LedgerClient.append` concurrently
are serialised by the connection's internal mutex plus the fact that the
append method is synchronous — no await points between SELECT last this_hash
and INSERT new row. This test proves that chain integrity holds when 5 tasks
all kick off append against the same client.

The multi-connection scenario (two `open_decisions_duckdb` handles on the
same file) is deferred to V1.1+ (see deferred-work.md entry `concurrent
multi-connection append`) — skipping here is an explicit contract rather
than silent non-coverage.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from athena.execution.ledger import LedgerClient
from athena.execution.ledger.hash_chain import compute_entry_hash
from athena.feature_store.duckdb_client import open_decisions_duckdb

pytestmark = pytest.mark.integration


def test_five_asyncio_tasks_preserve_chain(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    with open_decisions_duckdb(db_path) as conn:
        client = LedgerClient(conn)

        async def _worker(idx: int) -> int:
            return client.append(
                event_type="schema_segment_transition",
                payload={"worker": idx},
            )

        async def _run() -> list[int]:
            return await asyncio.gather(*(_worker(i) for i in range(5)))

        ids = asyncio.run(_run())
        # All 5 appends landed, ids are unique (sequence advanced per call).
        assert sorted(ids) == [2, 3, 4, 5, 6]

        rows = conn.execute(
            "SELECT id, event_type, policy_version_git_sha, user_id, "
            "payload_json, prev_hash, this_hash FROM pre_trade_ledger ORDER BY id"
        ).fetchall()
        assert len(rows) == 6  # genesis + 5 workers

        # Chain integrity: prev_hash(n) == this_hash(n-1), recomputed hashes
        # match stored hashes — enforces that cooperative interleaving did
        # not observe a stale `last this_hash`.
        prev_stored_this = None
        for row in rows:
            _, ev, psha, uid, pj, prev, this = row
            if prev is not None:
                assert prev == prev_stored_this
            expected = compute_entry_hash(
                prev_hash=prev,
                payload_json=pj,
                policy_version_git_sha=psha,
                event_type=ev,
                user_id=uid,
            )
            assert expected == this
            prev_stored_this = this


@pytest.mark.skip(reason="V1.1+ — multi-writer scope lock not implemented")
def test_multi_connection_append_is_deferred(tmp_path: Path) -> None:
    """Explicit skip — opening two DuckDB connections against the same .duckdb
    file and calling append on both concurrently is a V1.1+ concern. The
    single-writer invariant (architecture.md D13) forbids it in V1.0.
    deferred-work.md tracks the followup."""
