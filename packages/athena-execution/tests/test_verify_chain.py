"""Story 1.5 Task 6.3 — verify_chain unit scenarios (AC-6 "Then").

Stage-2 (no marker) — DuckDB :memory: only.

Covers AC-6 Then 1-5: clean chain, tampered payload, broken prev chain,
genesis special case, and segment continuity re-derivation."""

from __future__ import annotations

# Import the script-module's verify_chain without running its argparse main.
# scripts/ is not a package; add the directory to sys.path for this one test.
import sys
from pathlib import Path

import duckdb
from athena.execution.ledger import LedgerClient
from athena.execution.ledger.segment_hash import compute_segment_hash

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import verify_ledger  # type: ignore[import-not-found]  # noqa: E402


def _seeded_conn() -> tuple[duckdb.DuckDBPyConnection, LedgerClient]:
    conn = duckdb.connect(":memory:")
    client = LedgerClient(conn)
    for i in range(3):
        client.append(event_type="schema_segment_transition", payload={"i": i})
    return conn, client


def test_clean_chain_has_no_mismatches() -> None:
    conn, _ = _seeded_conn()
    assert verify_ledger.verify_chain(conn) == []


def test_tampered_payload_is_detected_as_this_hash_mismatch() -> None:
    conn, _ = _seeded_conn()
    # Simulate a DB-level tamper — application path forbids UPDATE, but a
    # motivated attacker bypassing the application layer would look like this.
    conn.execute(
        "UPDATE pre_trade_ledger_raw SET payload_json = ? WHERE id = 2",
        ['{"tampered":true}'],
    )
    mismatches = verify_ledger.verify_chain(conn)
    kinds = {(m["id"], m["kind"]) for m in mismatches}
    assert (2, "this_hash_mismatch") in kinds


def test_broken_prev_hash_is_detected_and_downstream_recompute_is_independent() -> None:
    conn, _ = _seeded_conn()
    conn.execute(
        "UPDATE pre_trade_ledger_raw SET prev_hash = ? WHERE id = 3",
        ["de" * 32],
    )
    mismatches = verify_ledger.verify_chain(conn)
    kinds = {(m["id"], m["kind"]) for m in mismatches}
    assert (3, "prev_hash_chain_break") in kinds
    # Downstream rows (id=4) are still independently hash-consistent — the
    # payload / this_hash pair at id=4 was not altered.
    assert (4, "this_hash_mismatch") not in kinds


def test_genesis_with_null_prev_hash_is_not_a_chain_break() -> None:
    conn = duckdb.connect(":memory:")
    LedgerClient(conn)  # genesis only
    # No tamper — genesis has prev_hash=NULL, last_this=None ⇒ allowed.
    assert verify_ledger.verify_chain(conn) == []


def test_segment_continuity_re_derives_from_prev_hash() -> None:
    conn, _ = _seeded_conn()
    row = conn.execute(
        "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
        "FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])
    # Compute prev-month segment hash (using empty month) as a sentinel prev.
    sentinel_prev = compute_segment_hash(
        conn,
        year=2020,
        month=1,  # empty month — no entries
        prev_segment_hash=None,
        policy_version_git_sha="aaaaaaaaaa",
    ).segment_hash
    seg = compute_segment_hash(
        conn,
        year=year,
        month=month,
        prev_segment_hash=sentinel_prev,
        policy_version_git_sha="aaaaaaaaaa",
    )
    assert seg.prev_segment_hash == sentinel_prev
    # Re-running is deterministic.
    seg2 = compute_segment_hash(
        conn,
        year=year,
        month=month,
        prev_segment_hash=sentinel_prev,
        policy_version_git_sha="aaaaaaaaaa",
    )
    assert seg.segment_hash == seg2.segment_hash
